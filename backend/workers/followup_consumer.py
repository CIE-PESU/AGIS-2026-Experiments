import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer

logger = logging.getLogger("followup_consumer")

CONSUMER_GROUP = "followup_worker_group"

class FollowupConsumer:
    def __init__(self, bootstrap_servers, executor, db):
        self.bootstrap_servers = bootstrap_servers
        self.executor = executor
        self.db = db
        self.consumer = None
        self._task = None

    async def start(self):
        try:
            from kafka.topics import KafkaTopics
            topic = KafkaTopics.FOLLOWUP
        except (ImportError, AttributeError):
            topic = "userSession.followup"
            
        self.consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=CONSUMER_GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        await self.consumer.start()
        self._task = asyncio.create_task(self._consume_loop())
        logger.info(f"Followup consumer started, listening on {CONSUMER_GROUP}")

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self.consumer:
            await self.consumer.stop()

    async def _consume_loop(self):
        try:
            async for message in self.consumer:
                await self._handle_message(message.value)
                await self.consumer.commit()
        except asyncio.CancelledError:
            logger.info("Followup consumer loop cancelled")

    async def _handle_message(self, raw_value: dict):
        session_id = raw_value.get("user_session_id")
        if not session_id:
            logger.error(f"Malformed message, no user_session_id: {raw_value}")
            return
            
        session = await self.db.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found in DB")
            return
            
        answer = session.get("pending_answer")
        if not answer:
            logger.error(f"No pending_answer found for session {session_id}")
            return
            
        logger.info(f"Resuming TIPSC executor for session {session_id}")
        await self.executor.resume_after_followup(session_id, answer)
