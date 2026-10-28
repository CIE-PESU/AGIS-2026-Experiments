# backend/app/kafka/producer.py
import asyncio
import json
import logging

from aiokafka import AIOKafkaProducer
from pydantic import BaseModel

from core.config import settings
from exceptions.base import KafkaPublishError

logger = logging.getLogger("kafka.producer")


class KafkaProducerClient:
    """Singleton Kafka Producer client managing async lifecycle and strict retries."""

    _instance = None
    _producer: AIOKafkaProducer | None = None
    is_running: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._producer = None
        return cls._instance

    async def start(self) -> None:
        """Initializes the producer. Called during backend startup events."""
        if self._producer is None:
            logger.info(
                "Initializing AIOKafkaProducer connecting to %s", settings.KAFKA_BOOTSTRAP_SERVERS
            )
            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                security_protocol=settings.KAFKA_SECURITY_PROTOCOL,
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            try:
                await self._producer.start()
                self.is_running = True
            except Exception:
                await self._producer.stop()
                self._producer = None
                raise
            logger.info("AIOKafkaProducer started successfully.")

    async def stop(self) -> None:
        """Stops the producer cleanly. Called during backend shutdown events."""
        self.is_running = False
        if self._producer is not None:
            logger.info("Stopping AIOKafkaProducer...")
            await self._producer.stop()
            self._producer = None
            logger.info("AIOKafkaProducer stopped cleanly.")

    async def check_health(self) -> bool:
        if not self.is_running or self._producer is None:
            return False
        try:
            await asyncio.wait_for(self._producer.client.fetch_all_metadata(), timeout=2)
            return True
        except Exception:
            return False

    async def publish(self, topic: str, payload: BaseModel) -> str:
        """
        Serializes and publishes a message to a specific topic with strict exponential backoff.
        Guarantees event ordering inside Kafka by forcing the partition key to be the session_id.
        """
        if self._producer is None:
            raise KafkaPublishError("Kafka producer is not initialized.")

        # Force messages under the same session to lock to the same partition sequentially
        message_value = payload.model_dump(mode="json")

        # Support both old and new Kafka schemas
        partition_key = getattr(payload, "session_id", None) or getattr(
            payload, "userSession_id", None
        )

        if partition_key is None:
            raise KafkaPublishError("Kafka payload has neither 'session_id' nor 'userSession_id'.")

        correlation_id = getattr(payload, "correlation_id", "")
        retries = 3
        backoff_delays = [0.1, 0.3, 0.9]  # 100ms, 300ms, 900ms backoffs

        for attempt in range(1, retries + 1):
            try:
                logger.debug(
                    "Publishing to %s [Attempt %d/%d] for Session %s, Correlation ID: %s",
                    topic,
                    attempt,
                    retries,
                    partition_key,
                    correlation_id,
                )

                # Send message asynchronously to cluster partition
                await self._producer.send_and_wait(
                    topic=topic, key=partition_key, value=message_value
                )

                logger.info(
                    "Successfully published message to %s. Correlation ID: %s",
                    topic,
                    correlation_id,
                )
                return correlation_id

            except Exception as e:
                logger.warning(
                    "Kafka send failed on attempt %d/%d for topic %s: %s",
                    attempt,
                    retries,
                    topic,
                    str(e),
                )
                if attempt < retries:
                    await asyncio.sleep(backoff_delays[attempt - 1])
                else:
                    logger.error(
                        "All %d retries exhausted for publishing event to %s.", retries, topic
                    )
                    raise KafkaPublishError(
                        f"Failed to publish event to Kafka topic '{topic}' after {retries} attempts."
                    ) from e

        raise KafkaPublishError("Publish attempts exhausted")


# Instantiate the global singleton client instance
kafka_producer = KafkaProducerClient()
