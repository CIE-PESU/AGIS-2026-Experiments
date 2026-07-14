"""
Notification worker.

Consumes userSession.notifications (published by DFV/TIPSC/Discovery workers
on completion/failure) and writes a polling-ready signal into the same
userSessions document the flow workers already write to.

This is what the frontend's 5s GET /userSession/{id} poller actually reads
to know "something changed, re-render" — without this worker, notification
events published by dfv_consumer.py just sit in Kafka with nobody reading
them.

Behavior:
- Idempotent: re-delivering the same notification just re-sets the same
  fields (safe no-op), and duplicate log entries are prevented by
  correlation_id + status dedup check.
- Malformed messages are logged and skipped, not fatal.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import ValidationError

from models.schema import NotificationMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("notification_worker")

KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
NOTIFICATIONS_TOPIC = "userSession.notifications"
CONSUMER_GROUP = "notification_worker_group"

MONGO_URI = "mongodb://127.0.0.1:27017"
DB_NAME = "agis"
USER_SESSIONS_COLLECTION = "sessions"


class NotificationWorker:
    def __init__(self):
        self.consumer: AIOKafkaConsumer | None = None
        self.mongo_client: AsyncIOMotorClient | None = None
        self.db = None

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            NOTIFICATIONS_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        self.mongo_client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.mongo_client[DB_NAME]

        await self.consumer.start()
        logger.info("Notification worker listening on %s (group=%s)",
                    NOTIFICATIONS_TOPIC, CONSUMER_GROUP)

    async def stop(self):
        if self.consumer:
            await self.consumer.stop()
        if self.mongo_client:
            self.mongo_client.close()

    async def _already_recorded(self, note: NotificationMessage) -> bool:
        """Skip if this exact notification (same correlation_id + status) was
        already written — avoids duplicate log entries on redelivery."""
        existing = await self.db[USER_SESSIONS_COLLECTION].find_one(
            {
                "_id": note.userSession_id,
                "notificationLog": {
                    "$elemMatch": {
                        "correlation_id": note.correlation_id,
                        "status": note.status.value,
                    }
                },
            }
        )
        return existing is not None

    async def _write_notification(self, note: NotificationMessage):
        """
        Writes two things to the session document:
          1. notifications.<flow>  — latest polling-ready signal for that flow,
             with `seen: false` so frontend can clear it once displayed.
          2. notificationLog       — append-only audit trail of every event,
             useful for debugging and for the idempotency dedup check above.
        """
        now = datetime.now(timezone.utc)

        await self.db[USER_SESSIONS_COLLECTION].update_one(
            {"_id": note.userSession_id},
            {
                "$set": {
                    f"notifications.{note.flow}": {
                        "status": note.status.value,
                        "idea_name": note.idea_name,
                        "error": note.error,
                        "emitted_at": note.emitted_at.isoformat(),
                        "seen": False,
                    }
                },
                "$push": {
                    "notificationLog": {
                        "flow": note.flow,
                        "correlation_id": note.correlation_id,
                        "status": note.status.value,
                        "idea_name": note.idea_name,
                        "error": note.error,
                        "recorded_at": now.isoformat(),
                    }
                },
            },
            upsert=True,
        )

    async def _handle_message(self, raw_value: dict):
        try:
            note = NotificationMessage(**raw_value)
        except ValidationError as e:
            logger.error(f"Malformed notification message, skipping: {e}")
            return

        if await self._already_recorded(note):
            logger.info(f"[correlation={note.correlation_id}] Already recorded — skipping")
            return

        await self._write_notification(note)
        logger.info(
            f"[correlation={note.correlation_id}] Recorded notification: "
            f"session={note.userSession_id} flow={note.flow} status={note.status.value}"
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
    worker = NotificationWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
