"""
events/shutdown.py — Application shutdown event handler.

Executed once when the FastAPI app shuts down. Cleans up:
  1. Kafka producer (graceful close)
  2. MongoDB connection (return pool connections)

Order is reverse of startup: close producers before DB.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def on_shutdown() -> None:
    """
    FastAPI lifespan shutdown handler.

    Called automatically by the lifespan context manager in main.py.
    Errors here are logged but not re-raised — shutdown must always complete.
    """
    logger.info("=== AGIS Backend Shutting Down ===")

    # ── 1. Kafka Producer ──────────────────────────────────────────────────────
    # Vijay's producer — will be wired in when B-06 merges.
    # try:
    #     from app.kafka.producer import kafka_producer
    #     await kafka_producer.stop()
    #     logger.info("[shutdown] Kafka Producer closed ✓")
    # except Exception as exc:
    #     logger.error("[shutdown] Kafka Producer close error: %s", exc)

    # ── 2. MongoDB ─────────────────────────────────────────────────────────────
    try:
        from app.database.mongodb import disconnect_db
        await disconnect_db()
        logger.info("[shutdown] MongoDB closed ✓")
    except Exception as exc:
        logger.error("[shutdown] MongoDB close error: %s", exc)

    logger.info("=== AGIS Backend Stopped ===")
