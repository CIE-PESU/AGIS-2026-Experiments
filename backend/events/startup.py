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
import sys
import os

# Add TIPSC-Agent/src to PYTHONPATH so backend can import engine modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../TIPSC-Agent/src")))

logger = logging.getLogger(__name__)

# Global instances to be used by shutdown.py
preeval_consumer_instance = None
followup_consumer_instance = None


async def on_startup() -> None:
    """
    FastAPI lifespan startup handler.

    Called automatically by the lifespan context manager in main.py.
    Raises on failure — FastAPI will not serve traffic if startup fails.
    """
    logger.info("=== AGIS Backend Starting Up ===")

    # ── 1. MongoDB ─────────────────────────────────────────────────────────────
    try:
        from database.mongodb import connect_db
        await connect_db()
        logger.info("[startup] MongoDB ✓")
    except Exception as exc:
        logger.critical("[startup] MongoDB connection FAILED: %s", exc)
        raise  # Hard fail — we cannot operate without the database

    # ── 2. Database Indexes ────────────────────────────────────────────────────
    # Bhavesh's indexes module — will be wired in when B-03 merges.
    try:
        from database.indexes import create_indexes
        await create_indexes()
        logger.info("[startup] Indexes ✓")
    except Exception as exc:
        logger.error("[startup] Index creation failed (non-fatal): %s", exc)

    # ── 3. Kafka Producer ──────────────────────────────────────────────────────
    try:
        from kafka.producer import kafka_producer
        await kafka_producer.start()
        logger.info("[startup] Kafka Producer ✓")
    except Exception as exc:
        logger.warning("[startup] Kafka Producer unavailable (non-fatal): %s", exc)

    # ── 4. Kafka Consumers for TIPSC ───────────────────────────────────────────
    try:
        from database.mongodb import get_client
        from engine.db import SessionStore
        from engine.stages import PipelineStages
        from engine.async_pipeline_executor import AsyncPipelineExecutor
        from workers.preeval_consumer import PreevalConsumer
        from workers.followup_consumer import FollowupConsumer
        from core.config import settings

        client = get_client()
        # Ensure we connect to the right collection. SessionStore expects the collection object.
        db = SessionStore(client[settings.MONGODB_DB_NAME]["userSessions"])
        
        # Instantiate pipeline stages with empty config or defaults as needed by the agent
        stages = PipelineStages(config_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../TIPSC-Agent/config")))
        executor = AsyncPipelineExecutor(stages, db)

        global preeval_consumer_instance, followup_consumer_instance
        preeval_consumer_instance = PreevalConsumer(settings.KAFKA_BOOTSTRAP_SERVERS, executor, db)
        followup_consumer_instance = FollowupConsumer(settings.KAFKA_BOOTSTRAP_SERVERS, executor, db)

        await preeval_consumer_instance.start()
        await followup_consumer_instance.start()
        logger.info("[startup] Kafka Consumers (Preeval/Followup) ✓")
    except Exception as exc:
        logger.error("[startup] Kafka Consumers startup failed (non-fatal): %s", exc)

    logger.info("=== AGIS Backend Ready ===")
