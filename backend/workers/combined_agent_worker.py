"""
Combined Agent Worker.

Consumes userSession.dfv and userSession.discovery.
Runs the CrewAI agents natively by importing them from their respective project folders.
Updates MongoDB and publishes to userSession.notifications.
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime, timezone

# Add agent directories to sys.path so we can import them
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
dfv_path = os.path.join(PROJECT_ROOT, "DFV-agent")
discovery_path = os.path.join(PROJECT_ROOT, "customer-interview-planner-agent")

if dfv_path not in sys.path:
    sys.path.append(dfv_path)
if discovery_path not in sys.path:
    sys.path.append(discovery_path)

# Now import the agents
from main import run_analysis as run_dfv_analysis
from customer_interview_planner import run_discovery_analysis

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import ValidationError

from models.schema import (
    DFVJobMessage, DiscoveryJobMessage, NotificationMessage, 
    DeadLetterMessage, DiscoveryDeadLetterMessage, FlowStatus
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("combined_agent_worker")

KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
DFV_TOPIC = "userSession.dfv"
DFV_DLQ_TOPIC = "userSession.dfv.dlq"
DISCOVERY_TOPIC = "userSession.discovery"
DISCOVERY_DLQ_TOPIC = "userSession.discovery.dlq"
NOTIFICATIONS_TOPIC = "userSession.notifications"
CONSUMER_GROUP = "combined_agent_worker_group"

MAX_RETRIES = 3
CREWAI_TIMEOUT_SECONDS = 600

MONGO_URI = "mongodb://127.0.0.1:27017"
DB_NAME = "agis"
USER_SESSIONS_COLLECTION = "userSessions"


def _log(correlation_id: str, msg: str, level: str = "info"):
    getattr(logger, level)(f"[correlation={correlation_id}] {msg}")


class CombinedAgentWorker:
    def __init__(self):
        self.consumer_dfv: AIOKafkaConsumer | None = None
        self.consumer_discovery: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None
        self.mongo_client: AsyncIOMotorClient | None = None
        self.db = None
        # Shared lock to prevent concurrent CrewAI executions overloading the LLM
        self._crew_lock = asyncio.Lock()

    async def start(self):
        # We need two consumers since they might have different deserialization needs,
        # but here we can just use two consumer instances listening to different topics.
        self.consumer_dfv = AIOKafkaConsumer(
            DFV_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP + "_dfv",
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            session_timeout_ms=120000,
            heartbeat_interval_ms=20000,
            max_poll_interval_ms=1800000,
        )
        self.consumer_discovery = AIOKafkaConsumer(
            DISCOVERY_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP + "_discovery",
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            session_timeout_ms=120000,
            heartbeat_interval_ms=20000,
            max_poll_interval_ms=1800000,
        )
        self.producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
        self.mongo_client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.mongo_client[DB_NAME]

        await self.consumer_dfv.start()
        await self.consumer_discovery.start()
        await self.producer.start()
        logger.info("Combined worker listening on %s and %s", DFV_TOPIC, DISCOVERY_TOPIC)

    async def stop(self):
        if self.consumer_dfv:
            await self.consumer_dfv.stop()
        if self.consumer_discovery:
            await self.consumer_discovery.stop()
        if self.producer:
            await self.producer.stop()
        if self.mongo_client:
            self.mongo_client.close()

    # -- DB Helpers -----------------------------------------------------------

    async def _already_done(self, user_session_id: str, correlation_id: str, flow_field: str) -> bool:
        existing = await self.db[USER_SESSIONS_COLLECTION].find_one(
            {
                "_id": user_session_id,
                f"{flow_field}.correlation_id": correlation_id,
                f"{flow_field}.status": FlowStatus.DONE.value,
            }
        )
        return existing is not None

    async def _write_status(self, user_session_id: str, correlation_id: str, flow_field: str, status: FlowStatus, retry_count: int,
                            output=None, error=None, started_at=None, completed_at=None, extra_data=None):
        update_data = {
            "correlation_id": correlation_id,
            "status": status.value,
            "output": output,
            "error": error,
            "started_at": started_at,
            "completed_at": completed_at,
            "retry_count": retry_count,
        }
        if extra_data:
            update_data.update(extra_data)

        # Update both the nested flow state and the root session status
        root_status = f"{flow_field}_{status.value}" if status.value != FlowStatus.DONE.value else f"{flow_field}_completed"
        # If discovery is completed, the whole session is completed
        if flow_field == "discovery" and status.value == FlowStatus.DONE.value:
            root_status = "completed"

        await self.db[USER_SESSIONS_COLLECTION].update_one(
            {"_id": user_session_id},
            {"$set": {
                flow_field: update_data,
                "status": root_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True,
        )

    async def _publish_notification(self, user_session_id: str, correlation_id: str, flow: str, status: FlowStatus,
                                    error: str | None = None, idea_name: str | None = None):
        note = NotificationMessage(
            userSession_id=user_session_id,
            correlation_id=correlation_id,
            flow=flow,
            status=status,
            idea_name=idea_name,
            error=error,
        )
        await self.producer.send_and_wait(
            NOTIFICATIONS_TOPIC,
            value=note.model_dump_json().encode("utf-8"),
            key=user_session_id.encode("utf-8"),
        )

    # -- DFV Processing -------------------------------------------------------

    async def _process_dfv_job(self, job: DFVJobMessage):
        if await self._already_done(job.userSession_id, job.correlation_id, "dfv"):
            _log(job.correlation_id, "DFV Already processed (idempotency check) — skipping")
            return

        started_at = datetime.now(timezone.utc)
        await self._write_status(job.userSession_id, job.correlation_id, "dfv", FlowStatus.RUNNING, job.retry_count,
                                 started_at=started_at, extra_data={"idea_name": job.idea_name})
        _log(job.correlation_id, f"Starting DFV analysis for '{job.idea_name}'")

        try:
            async with self._crew_lock:
                result = await asyncio.wait_for(
                    asyncio.to_thread(run_dfv_analysis, job.payload.model_dump()),
                    timeout=CREWAI_TIMEOUT_SECONDS,
                )

            try:
                parsed = json.loads(result.raw)
            except Exception:
                parsed = {"raw": result.raw}

            completed_at = datetime.now(timezone.utc)
            await self._write_status(
                job.userSession_id, job.correlation_id, "dfv", FlowStatus.DONE, job.retry_count,
                output=parsed, started_at=started_at, completed_at=completed_at, extra_data={"idea_name": job.idea_name}
            )
            await self._publish_notification(job.userSession_id, job.correlation_id, "dfv", FlowStatus.DONE, idea_name=job.idea_name)

            decision = parsed.get("final_decision", {}).get("status", "unknown")
            _log(job.correlation_id, f"Done: {job.idea_name} | decision={decision}")

        except asyncio.TimeoutError:
            await self._write_status(job.userSession_id, job.correlation_id, "dfv", FlowStatus.TIMEOUT, job.retry_count,
                                     error="CrewAI run exceeded timeout", started_at=started_at, extra_data={"idea_name": job.idea_name})
            await self._publish_notification(job.userSession_id, job.correlation_id, "dfv", FlowStatus.TIMEOUT, error="timeout", idea_name=job.idea_name)
            raise
        except Exception as e:
            await self._write_status(job.userSession_id, job.correlation_id, "dfv", FlowStatus.FAILED, job.retry_count,
                                     error=str(e), started_at=started_at, extra_data={"idea_name": job.idea_name})
            raise

    async def _handle_dfv_message(self, raw_value: dict):
        try:
            job = DFVJobMessage(**raw_value)
        except ValidationError as e:
            logger.error(f"Malformed DFV message, sending to DLQ raw: {e}")
            await self.producer.send_and_wait(DFV_DLQ_TOPIC, value=json.dumps(raw_value).encode("utf-8"))
            return

        try:
            await self._process_dfv_job(job)
        except Exception as e:
            job.retry_count += 1
            if job.retry_count > MAX_RETRIES:
                dlq_msg = DeadLetterMessage(original_message=job, failure_reason=str(e))
                await self.producer.send_and_wait(
                    DFV_DLQ_TOPIC,
                    value=dlq_msg.model_dump_json().encode("utf-8"),
                    key=job.userSession_id.encode("utf-8"),
                )
                await self._publish_notification(job.userSession_id, job.correlation_id, "dfv", FlowStatus.FAILED, error=str(e))
            else:
                _log(job.correlation_id, f"DFV Retry {job.retry_count}/{MAX_RETRIES} after error: {e}", level="warning")
                await self.producer.send_and_wait(
                    DFV_TOPIC,
                    value=job.model_dump_json().encode("utf-8"),
                    key=job.userSession_id.encode("utf-8"),
                )

    # -- Discovery Processing -------------------------------------------------

    async def _process_discovery_job(self, job: DiscoveryJobMessage):
        if await self._already_done(job.userSession_id, job.correlation_id, "discovery"):
            _log(job.correlation_id, "Discovery Already processed (idempotency check) — skipping")
            return

        started_at = datetime.now(timezone.utc)
        await self._write_status(job.userSession_id, job.correlation_id, "discovery", FlowStatus.RUNNING, job.retry_count, started_at=started_at)
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
                parsed = {"raw": result.raw}

            completed_at = datetime.now(timezone.utc)
            await self._write_status(
                job.userSession_id, job.correlation_id, "discovery", FlowStatus.DONE, job.retry_count,
                output=parsed, started_at=started_at, completed_at=completed_at
            )
            await self._publish_notification(job.userSession_id, job.correlation_id, "discovery", FlowStatus.DONE)

            _log(job.correlation_id, "Done: Discovery plan generated")

        except asyncio.TimeoutError:
            await self._write_status(job.userSession_id, job.correlation_id, "discovery", FlowStatus.TIMEOUT, job.retry_count,
                                     error="CrewAI run exceeded timeout", started_at=started_at)
            await self._publish_notification(job.userSession_id, job.correlation_id, "discovery", FlowStatus.TIMEOUT, error="timeout")
            raise
        except Exception as e:
            await self._write_status(job.userSession_id, job.correlation_id, "discovery", FlowStatus.FAILED, job.retry_count,
                                     error=str(e), started_at=started_at)
            raise

    async def _handle_discovery_message(self, raw_value: dict):
        try:
            job = DiscoveryJobMessage(**raw_value)
        except ValidationError as e:
            logger.error(f"Malformed Discovery message, sending to DLQ raw: {e}")
            await self.producer.send_and_wait(DISCOVERY_DLQ_TOPIC, value=json.dumps(raw_value).encode("utf-8"))
            return

        try:
            await self._process_discovery_job(job)
        except Exception as e:
            job.retry_count += 1
            if job.retry_count > MAX_RETRIES:
                dlq_msg = DiscoveryDeadLetterMessage(original_message=job, failure_reason=str(e))
                await self.producer.send_and_wait(
                    DISCOVERY_DLQ_TOPIC,
                    value=dlq_msg.model_dump_json().encode("utf-8"),
                    key=job.userSession_id.encode("utf-8"),
                )
                await self._publish_notification(job.userSession_id, job.correlation_id, "discovery", FlowStatus.FAILED, error=str(e))
            else:
                _log(job.correlation_id, f"Discovery Retry {job.retry_count}/{MAX_RETRIES} after error: {e}", level="warning")
                await self.producer.send_and_wait(
                    DISCOVERY_TOPIC,
                    value=job.model_dump_json().encode("utf-8"),
                    key=job.userSession_id.encode("utf-8"),
                )

    # -- Loops ----------------------------------------------------------------

    async def _consume_dfv(self):
        try:
            async for message in self.consumer_dfv:
                await self._handle_dfv_message(message.value)
                await self.consumer_dfv.commit()
        except asyncio.CancelledError:
            pass

    async def _consume_discovery(self):
        try:
            async for message in self.consumer_discovery:
                await self._handle_discovery_message(message.value)
                await self.consumer_discovery.commit()
        except asyncio.CancelledError:
            pass

    async def run(self):
        await self.start()
        try:
            await asyncio.gather(
                self._consume_dfv(),
                self._consume_discovery()
            )
        finally:
            await self.stop()

async def main():
    worker = CombinedAgentWorker()
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
