"""
events/startup.py — Application startup event handler.

Executed once when the FastAPI app starts. Initializes:
  1. MongoDB connection + Beanie ODM
  2. Kafka producer (Vijay's module — wired in on Day 1 merge)
  3. Database indexes (Bhavesh's module — wired in on Day 1 merge)

Order matters: DB must be ready before indexes can be created.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def on_startup() -> None:
    """
    FastAPI lifespan startup handler.

    Called automatically by the lifespan context manager in main.py.
    Raises on failure — FastAPI will not serve traffic if startup fails.
    """
    logger.info("=== AGIS Backend Starting Up ===")

    # ── 1. MongoDB ─────────────────────────────────────────────────────────────
    try:
        from app.database.mongodb import connect_db
        await connect_db()
        logger.info("[startup] MongoDB ✓")
    except Exception as exc:
        logger.critical("[startup] MongoDB connection FAILED: %s", exc)
        raise  # Hard fail — we cannot operate without the database

    # ── 2. Database Indexes ────────────────────────────────────────────────────
    # Bhavesh's indexes module — will be wired in when B-03 merges.
    try:
        from app.database.indexes import create_indexes
        await create_indexes()
        logger.info("[startup] Indexes ✓")
    except Exception as exc:
        logger.error("[startup] Index creation failed (non-fatal): %s", exc)

    # ── 3. Kafka Producer ──────────────────────────────────────────────────────
    # Vijay's producer — will be wired in when B-06 merges.
    # try:
    #     from app.kafka.producer import kafka_producer
    #     await kafka_producer.start()
    #     logger.info("[startup] Kafka Producer ✓")
    # except Exception as exc:
    #     logger.warning("[startup] Kafka Producer unavailable (non-fatal): %s", exc)

    logger.info("=== AGIS Backend Ready ===")
