"""
DFV consumer worker.

Consumes userSession.dfv, runs the CrewAI DFV crew, writes results to MongoDB,
and publishes completion/failure events to userSession.notifications.

Reliability behavior:
- Idempotent: skips jobs already marked 'done' for a given correlation_id.
- Retries transient failures up to MAX_RETRIES, then routes to DLQ.
- Times out CrewAI calls that hang (local LM Studio can stall).
- Every log line carries correlation_id for tracing.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import ValidationError

from models.schema import DFVJobMessage, NotificationMessage, DeadLetterMessage, FlowStatus
from main import run_analysis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dfv_worker")

KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
DFV_TOPIC = "userSession.dfv"
DFV_DLQ_TOPIC = "userSession.dfv.dlq"
NOTIFICATIONS_TOPIC = "userSession.notifications"
CONSUMER_GROUP = "dfv_worker_group"

MAX_RETRIES = 3
CREWAI_TIMEOUT_SECONDS = 600  # 10 min ceiling for a full DFV crew run

MONGO_URI = "mongodb://127.0.0.1:27017"  # default local mongod, same one Compass connects to
DB_NAME = "agis"
# Assumption pending backend confirmation: one collection, one document per
# session, each flow lives under its own sub-field (session["dfv"] = {...}).
USER_SESSIONS_COLLECTION = "userSessions"


def _log(correlation_id: str, msg: str, level: str = "info"):
    getattr(logger, level)(f"[correlation={correlation_id}] {msg}")


class DFVConsumer:
    def __init__(self):
        self.consumer: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None
        self.mongo_client: AsyncIOMotorClient | None = None
        self.db = None

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            DFV_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        self.producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
        self.mongo_client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.mongo_client[DB_NAME]

        await self.consumer.start()
        await self.producer.start()
        logger.info("DFV worker listening on %s (group=%s)", DFV_TOPIC, CONSUMER_GROUP)

    async def stop(self):
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        if self.mongo_client:
            self.mongo_client.close()

    # -- idempotency -------------------------------------------------------

    async def _already_done(self, job: DFVJobMessage) -> bool:
        existing = await self.db[USER_SESSIONS_COLLECTION].find_one(
            {"_id": job.userSession_id, "dfv.correlation_id": job.correlation_id, "dfv.status": FlowStatus.DONE.value}
        )
        return existing is not None

    # -- mongo status writes -------------------------------------------------
    # Writes only to this session's "dfv" sub-field via $set, so TIPSC/discovery
    # data on the same document (written by other workers) is untouched.

    async def _write_status(self, job: DFVJobMessage, status: FlowStatus, output=None, error=None,
                             started_at=None, completed_at=None):
        await self.db[USER_SESSIONS_COLLECTION].update_one(
            {"_id": job.userSession_id},
            {
                "$set": {
                    "dfv": {
                        "idea_name": job.idea_name,
                        "correlation_id": job.correlation_id,
                        "status": status.value,
                        "output": output,
                        "error": error,
                        "started_at": started_at,
                        "completed_at": completed_at,
                        "retry_count": job.retry_count,
                    }
                }
            },
            upsert=True,
        )

    # -- notification publish ----------------------------------------------

    async def _publish_notification(self, job: DFVJobMessage, status: FlowStatus, error: str | None = None):
        note = NotificationMessage(
            userSession_id=job.userSession_id,
            correlation_id=job.correlation_id,
            status=status,
            idea_name=job.idea_name,
            error=error,
        )
        await self.producer.send_and_wait(
            NOTIFICATIONS_TOPIC,
            value=note.model_dump_json().encode("utf-8"),
            key=job.userSession_id.encode("utf-8"),
        )

    # -- dead letter ----------------------------------------------------------

    async def _send_to_dlq(self, job: DFVJobMessage, reason: str):
        dlq_msg = DeadLetterMessage(original_message=job, failure_reason=reason)
        await self.producer.send_and_wait(
            DFV_DLQ_TOPIC,
            value=dlq_msg.model_dump_json().encode("utf-8"),
            key=job.userSession_id.encode("utf-8"),
        )
        _log(job.correlation_id, f"Sent to DLQ after {job.retry_count} retries: {reason}", level="error")

    # -- core processing --------------------------------------------------

    async def _process_job(self, job: DFVJobMessage):
        if await self._already_done(job):
            _log(job.correlation_id, "Already processed (idempotency check) — skipping")
            return

        started_at = datetime.now(timezone.utc)
        await self._write_status(job, FlowStatus.RUNNING, started_at=started_at)
        _log(job.correlation_id, f"Starting DFV analysis for '{job.idea_name}'")

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(run_analysis, job.payload.model_dump()),
                timeout=CREWAI_TIMEOUT_SECONDS,
            )

            try:
                parsed = json.loads(result.raw)
            except Exception:
                parsed = {"raw": result.raw}

            completed_at = datetime.now(timezone.utc)
            await self._write_status(
                job, FlowStatus.DONE, output=parsed, started_at=started_at, completed_at=completed_at
            )
            await self._publish_notification(job, FlowStatus.DONE)

            decision = parsed.get("final_decision", {}).get("status", "unknown")
            _log(job.correlation_id, f"Done: {job.idea_name} | decision={decision}")

        except asyncio.TimeoutError:
            await self._write_status(job, FlowStatus.TIMEOUT, error="CrewAI run exceeded timeout",
                                      started_at=started_at)
            await self._publish_notification(job, FlowStatus.TIMEOUT, error="timeout")
            raise

        except Exception as e:
            await self._write_status(job, FlowStatus.FAILED, error=str(e), started_at=started_at)
            raise

    async def _handle_message(self, raw_value: dict):
        try:
            job = DFVJobMessage(**raw_value)
        except ValidationError as e:
            logger.error(f"Malformed message, sending to DLQ raw: {e}")
            await self.producer.send_and_wait(DFV_DLQ_TOPIC, value=json.dumps(raw_value).encode("utf-8"))
            return

        try:
            await self._process_job(job)
        except Exception as e:
            job.retry_count += 1
            if job.retry_count > MAX_RETRIES:
                await self._send_to_dlq(job, reason=str(e))
                await self._publish_notification(job, FlowStatus.FAILED, error=str(e))
            else:
                _log(job.correlation_id, f"Retry {job.retry_count}/{MAX_RETRIES} after error: {e}",
                     level="warning")
                await self.producer.send_and_wait(
                    DFV_TOPIC,
                    value=job.model_dump_json().encode("utf-8"),
                    key=job.userSession_id.encode("utf-8"),
                )

    async def run(self):
        await self.start()
        try:
            async for message in self.consumer:
                await self._handle_message(message.value)
                await self.consumer.commit()
        finally:
            await self.stop()


async def main():
    worker = DFVConsumer()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
