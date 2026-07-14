"""
workers/base_worker.py — Abstract base class for all Kafka workers.

Eliminates boilerplate duplication across combined_agent_worker.py,
notification_worker.py, and any future workers.

Usage:
    class MyWorker(BaseKafkaWorker):
        def get_topic(self) -> str: return "my.topic"
        def get_group_id(self) -> str: return "my-group"
        async def process_message(self, raw_value: dict) -> None:
            ...

    asyncio.run(MyWorker().run())
"""

import asyncio
import logging
import os
import signal
from abc import ABC, abstractmethod
from typing import Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger(__name__)


class BaseKafkaWorker(ABC):
    """
    Abstract base for all AGIS Kafka workers.

    Subclasses implement:
        get_topic()               → str:  The Kafka topic to subscribe to.
        get_group_id()            → str:  The consumer group ID.
        process_message(raw_value) → None: Per-message handler.

    The base handles:
        - Consumer/producer lifecycle (start + graceful stop)
        - Signal handling (SIGINT / SIGTERM → clean shutdown)
        - Auto-commit after successful processing
        - Error logging without crashing the loop
        - Optional HTTP health endpoint (port via WORKER_HEALTH_PORT env var)
    """

    def __init__(self) -> None:
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._producer: Optional[AIOKafkaProducer] = None
        self._mongo_client: Optional[AsyncIOMotorClient] = None
        self._running = False
        self._kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
        self._mongo_uri = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
        self._db_name = os.getenv("MONGODB_DB_NAME", "agis")
        self._health_port = int(os.getenv("WORKER_HEALTH_PORT", "0"))  # 0 = disabled

    # ── Abstract interface ─────────────────────────────────────────────────────

    @abstractmethod
    def get_topic(self) -> str: ...

    @abstractmethod
    def get_group_id(self) -> str: ...

    @abstractmethod
    async def process_message(self, raw_value: dict) -> None: ...

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Connect to Kafka and MongoDB, then begin consuming."""
        self._consumer = AIOKafkaConsumer(
            self.get_topic(),
            bootstrap_servers=self._kafka_servers,
            group_id=self.get_group_id(),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda m: __import__("json").loads(m.decode("utf-8")),
            session_timeout_ms=120_000,
            heartbeat_interval_ms=20_000,
            max_poll_interval_ms=1_800_000,
        )
        self._producer = AIOKafkaProducer(bootstrap_servers=self._kafka_servers)
        self._mongo_client = AsyncIOMotorClient(self._mongo_uri)
        self.db = self._mongo_client[self._db_name]  # type: ignore[attr-defined]

        await self._consumer.start()
        await self._producer.start()
        self._running = True
        logger.info(
            "[%s] Started — listening on topic '%s' (group=%s)",
            self.__class__.__name__,
            self.get_topic(),
            self.get_group_id(),
        )

    async def stop(self) -> None:
        """Gracefully drain and close all connections."""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()
        if self._mongo_client:
            self._mongo_client.close()
        logger.info("[%s] Stopped.", self.__class__.__name__)

    # ── Main run loop ──────────────────────────────────────────────────────────

    async def run(self) -> None:
        """
        Entry point. Registers signal handlers, starts connections, then
        processes messages until stopped.
        """
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        await self.start()

        # Optionally start health probe server in background
        if self._health_port > 0:
            asyncio.create_task(self._health_server(self._health_port))

        try:
            async for message in self._consumer:  # type: ignore[union-attr]
                if not self._running:
                    break
                try:
                    await self.process_message(message.value)
                    await self._consumer.commit()  # type: ignore[union-attr]
                except Exception as exc:
                    logger.error(
                        "[%s] Error processing message: %s",
                        self.__class__.__name__,
                        exc,
                        exc_info=True,
                    )
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    # ── Health endpoint (Issue 23 / Task 3.5-D) ────────────────────────────────

    async def _health_server(self, port: int) -> None:
        """
        Minimal aiohttp HTTP server for container liveness probes.
        Set WORKER_HEALTH_PORT env var to enable (e.g. 8001 for combined, 8002 for notification).

        GET /health → 200 {"status": "ok", "worker": "...", "topic": "...", "running": true}
        """
        try:
            from aiohttp import web  # optional dep — only needed when health port is set

            async def health(request: web.Request) -> web.Response:  # noqa: ARG001
                return web.json_response({
                    "status": "ok" if self._running else "stopped",
                    "worker": self.__class__.__name__,
                    "topic": self.get_topic(),
                    "group_id": self.get_group_id(),
                    "running": self._running,
                })

            app = web.Application()
            app.router.add_get("/health", health)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", port)
            await site.start()
            logger.info(
                "[%s] Health endpoint: http://0.0.0.0:%d/health",
                self.__class__.__name__,
                port,
            )
        except ImportError:
            logger.warning(
                "[%s] aiohttp not installed — health endpoint disabled. "
                "Run: pip install aiohttp",
                self.__class__.__name__,
            )
        except Exception as exc:
            logger.error("[%s] Health server failed to start: %s", self.__class__.__name__, exc)
