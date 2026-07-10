"""
Discovery consumer worker.

Consumes userSession.discovery, runs the Customer Discovery Planner crew,
writes results to MongoDB, and publishes completion/failure events to
userSession.notifications (shared topic with the DFV worker).

Reliability behavior — same pattern as workers/dfv_consumer.py in the
DFV-agent project:
- Idempotent: skips jobs already marked 'done' for a given correlation_id.
- Retries transient failures up to MAX_RETRIES, then routes to DLQ.
- Times out CrewAI calls that hang (local LM Studio can stall).
- Serializes CrewAI execution via a lock — main.py-style agents are
  module-level singletons, not safe to invoke concurrently.
- Every log line carries correlation_id for tracing.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import ValidationError

from models.schema import DiscoveryJobMessage, NotificationMessage, DiscoveryDeadLetterMessage, FlowStatus
from customer_interview_planner import run_discovery_analysis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("discovery_worker")

KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
DISCOVERY_TOPIC = "userSession.discovery"
DISCOVERY_DLQ_TOPIC = "userSession.discovery.dlq"
NOTIFICATIONS_TOPIC = "userSession.notifications"
CONSUMER_GROUP = "discovery_worker_group"

MAX_RETRIES = 3
CREWAI_TIMEOUT_SECONDS = 600  # 10 min ceiling for a full Discovery plan run

MONGO_URI = "mongodb://127.0.0.1:27017"
DB_NAME = "agis"
USER_SESSIONS_COLLECTION = "userSessions"  # shared collection with DFV; only touches its own "discovery" sub-field


def _log(correlation_id: str, msg: str, level: str = "info"):
    getattr(logger, level)(f"[correlation={correlation_id}] {msg}")


class DiscoveryConsumer:
    def __init__(self):
        self.consumer: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None
        self.mongo_client: AsyncIOMotorClient | None = None
        self.db = None
        # customer_interview_planner.py's Agent is a module-level singleton,
        # not thread-safe for concurrent invocation. Same fix as DFV's
        # consumer — only one crew run executes at a time.
        self._crew_lock = asyncio.Lock()

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            DISCOVERY_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            # Same heartbeat-starvation fix as the DFV consumer: a long
            # CrewAI run in a background thread can delay heartbeats
            # enough that Kafka kicks the consumer from the group.
            session_timeout_ms=120000,
            heartbeat_interval_ms=20000,
            max_poll_interval_ms=1800000,
        )
        self.producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
        self.mongo_client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.mongo_client[DB_NAME]

        await self.consumer.start()
        await self.producer.start()
        logger.info("Discovery worker listening on %s (group=%s)", DISCOVERY_TOPIC, CONSUMER_GROUP)

    async def stop(self):
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        if self.mongo_client:
            self.mongo_client.close()

    # -- idempotency -------------------------------------------------------

    async def _already_done(self, job: DiscoveryJobMessage) -> bool:
        existing = await self.db[USER_SESSIONS_COLLECTION].find_one(
            {
                "_id": job.userSession_id,
                "discovery.correlation_id": job.correlation_id,
                "discovery.status": FlowStatus.DONE.value,
            }
        )
        return existing is not None

    # -- mongo status writes -------------------------------------------------
    # Writes only to this session's "discovery" sub-field via $set, so DFV/
    # TIPSC data on the same document (written by other workers) is untouched.

    async def _write_status(self, job: DiscoveryJobMessage, status: FlowStatus, output=None, error=None,
                             started_at=None, completed_at=None):
        await self.db[USER_SESSIONS_COLLECTION].update_one(
            {"_id": job.userSession_id},
            {
                "$set": {
                    "discovery": {
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

    async def _publish_notification(self, job: DiscoveryJobMessage, status: FlowStatus, error: str | None = None):
        note = NotificationMessage(
            userSession_id=job.userSession_id,
            correlation_id=job.correlation_id,
            flow="discovery",
            status=status,
            idea_name=None,  # Discovery has no single "idea name"
            error=error,
        )
        await self.producer.send_and_wait(
            NOTIFICATIONS_TOPIC,
            value=note.model_dump_json().encode("utf-8"),
            key=job.userSession_id.encode("utf-8"),
        )

    # -- dead letter ----------------------------------------------------------

    async def _send_to_dlq(self, job: DiscoveryJobMessage, reason: str):
        dlq_msg = DiscoveryDeadLetterMessage(original_message=job, failure_reason=reason)
        await self.producer.send_and_wait(
            DISCOVERY_DLQ_TOPIC,
            value=dlq_msg.model_dump_json().encode("utf-8"),
            key=job.userSession_id.encode("utf-8"),
        )
        _log(job.correlation_id, f"Sent to DLQ after {job.retry_count} retries: {reason}", level="error")

    # -- core processing --------------------------------------------------

    async def _process_job(self, job: DiscoveryJobMessage):
        if await self._already_done(job):
            _log(job.correlation_id, "Already processed (idempotency check) — skipping")
            return

        started_at = datetime.now(timezone.utc)
        await self._write_status(job, FlowStatus.RUNNING, started_at=started_at)
        _log(job.correlation_id, "Starting Discovery plan analysis")

        try:
            async with self._crew_lock:
                result = await asyncio.wait_for(
                    asyncio.to_thread(run_discovery_analysis, job.payload.model_dump()),
                    timeout=CREWAI_TIMEOUT_SECONDS,
                )

            try:
                parsed = json.loads(result.raw)
            except Exception:
                # No structured output model yet (see customer_interview_planner.py /
                # README "Future Enhancements") — store as raw text for now.
                parsed = {"raw": result.raw}

            completed_at = datetime.now(timezone.utc)
            await self._write_status(
                job, FlowStatus.DONE, output=parsed, started_at=started_at, completed_at=completed_at
            )
            await self._publish_notification(job, FlowStatus.DONE)

            _log(job.correlation_id, "Done: Discovery plan generated")

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
            job = DiscoveryJobMessage(**raw_value)
        except ValidationError as e:
            logger.error(f"Malformed message, sending to DLQ raw: {e}")
            await self.producer.send_and_wait(DISCOVERY_DLQ_TOPIC, value=json.dumps(raw_value).encode("utf-8"))
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
                    DISCOVERY_TOPIC,
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
    worker = DiscoveryConsumer()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
