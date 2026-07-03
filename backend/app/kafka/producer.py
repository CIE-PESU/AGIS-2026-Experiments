"""
kafka/producer.py — Async Kafka producer wrapper.

Wraps aiokafka's AIOKafkaProducer with:
  - Lifecycle management (start/stop tied to FastAPI lifespan)
  - A single `publish()` helper used by services
  - Retry logic with exponential back-off
  - Structured logging on every publish

Usage:
    from app.kafka.producer import kafka_producer
    await kafka_producer.publish(topic=KafkaTopic.USER_SESSION_TIPSC, value=payload.model_dump_json())

Startup (in events/startup.py):
    await kafka_producer.start()

Shutdown (in events/shutdown.py):
    await kafka_producer.stop()
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Maximum number of times to retry a failed publish before giving up.
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 0.5  # seconds


class KafkaProducer:
    """
    Async Kafka producer with lifecycle management and retry logic.

    The underlying aiokafka producer is lazily imported so that the module
    can be imported in environments where aiokafka is not installed
    (e.g. running unit tests without a real Kafka broker).
    """

    def __init__(self) -> None:
        self._producer: Any = None
        self._started: bool = False

    async def start(self) -> None:
        """
        Initialise and start the aiokafka producer.
        Called once during FastAPI lifespan startup.
        """
        try:
            from aiokafka import AIOKafkaProducer  # type: ignore[import]

            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                security_protocol=settings.KAFKA_SECURITY_PROTOCOL,
                # JSON serialiser — all messages are UTF-8 JSON strings.
                value_serializer=lambda v: v.encode("utf-8") if isinstance(v, str) else json.dumps(v).encode("utf-8"),
                # Key serialiser (topic key = session_id for ordered delivery per session).
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                # Producer acks: wait for leader + 1 replica before confirming.
                acks="all",
                # Retry at the producer level before we raise.
                retries=2,
                max_batch_size=16384,
                linger_ms=5,
            )
            await self._producer.start()
            self._started = True
            logger.info(
                "Kafka producer started | brokers=%s", settings.KAFKA_BOOTSTRAP_SERVERS
            )
        except Exception as exc:
            # Kafka unavailability at startup is logged but does not crash the app.
            # Individual publish() calls will raise KafkaPublishError.
            logger.error("Kafka producer failed to start: %s", exc, exc_info=True)

    async def stop(self) -> None:
        """
        Gracefully flush and stop the aiokafka producer.
        Called once during FastAPI lifespan shutdown.
        """
        if self._producer and self._started:
            try:
                await self._producer.stop()
                self._started = False
                logger.info("Kafka producer stopped.")
            except Exception as exc:
                logger.warning("Kafka producer stop error (ignored): %s", exc)

    async def publish(
        self,
        topic: str,
        value: str,
        key: str | None = None,
    ) -> str:
        """
        Publish a JSON-serialised message to a Kafka topic.

        Retries up to _MAX_RETRIES times with exponential back-off.
        Generates and returns a correlation_id (UUID4) that the caller should
        store on the session for worker validation.

        Args:
            topic : Kafka topic name (use KafkaTopic constants).
            value : JSON string payload. Use payload.model_dump_json().
            key   : Optional partition key (e.g. session_id for ordered delivery).

        Returns:
            correlation_id : UUID4 string identifying this specific publish event.

        Raises:
            KafkaPublishError : After all retries are exhausted.
            KafkaUnavailableError : If the producer was never successfully started.
        """
        from app.exceptions.base import KafkaPublishError, KafkaUnavailableError

        if not self._started or self._producer is None:
            raise KafkaUnavailableError(
                "Kafka producer is not running. Check broker connectivity."
            )

        correlation_id = str(uuid.uuid4())
        last_exc: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                await self._producer.send_and_wait(
                    topic,
                    value=value,
                    key=key,
                )
                logger.info(
                    "Kafka message published | topic=%s | key=%s | correlation_id=%s | attempt=%d",
                    topic,
                    key,
                    correlation_id,
                    attempt,
                )
                return correlation_id
            except Exception as exc:
                last_exc = exc
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Kafka publish attempt %d/%d failed | topic=%s | error=%s | retry_in=%.1fs",
                    attempt,
                    _MAX_RETRIES,
                    topic,
                    exc,
                    delay,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(delay)

        logger.error(
            "Kafka publish failed after %d attempts | topic=%s | error=%s",
            _MAX_RETRIES,
            topic,
            last_exc,
        )
        raise KafkaPublishError(
            f"Failed to publish to topic '{topic}' after {_MAX_RETRIES} retries: {last_exc}"
        )


# Module-level singleton — started/stopped by lifespan hooks.
kafka_producer = KafkaProducer()
