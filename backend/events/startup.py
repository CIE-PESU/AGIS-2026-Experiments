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

# Global instances to be used by shutdown.py and routes
tipsc_executor_instance = None


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

    # ── 4. Setup TIPSC Engine (No Kafka for TIPSC) ───────────────────────────
    try:
        from database.mongodb import get_client
        from engine.db import SessionStore
        from engine.stages import PipelineStages
        from engine.async_pipeline_executor import AsyncPipelineExecutor
        from core.config import settings

        client = get_client()
        db = SessionStore(client[settings.MONGODB_DB_NAME]["sessions"])
        
        import json
        import yaml
        from pathlib import Path

        tipsc_src_dir = Path(__file__).resolve().parent.parent.parent / "TIPSC-Agent" / "src"
        
        def _load_yaml(rel: str):
            with open(tipsc_src_dir / rel, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
                
        def _load_text(rel: str):
            with open(tipsc_src_dir / rel, "r", encoding="utf-8") as f:
                return f.read()

        agents_cfg = _load_yaml("config/agents.yaml")
        task_cfg = _load_yaml("config/tasks.yaml")
        preeval_skill = _load_text("skills/preeval/SKILL.md")
        tipsc_rubric = _load_text("skills/tipsc/SKILL.md")
        ethics_rubric = _load_text("skills/ethics/SKILL.md")
        
        try:
            from crewai import LLM
            llm = LLM(
                model=os.getenv("OPENAI_MODEL_NAME", "lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF"),
                base_url=os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1"),
                api_key=os.getenv("OPENAI_API_KEY", "lm-studio"),
                temperature=0.2,
            )
        except Exception as e:
            logger.warning("[startup] Failed to initialize LLM for TIPSC: %s", e)
            llm = None

        
        stages = PipelineStages(
            llm=llm,
            agents_cfg=agents_cfg,
            task_cfg=task_cfg,
            preeval_skill=preeval_skill,
            tipsc_rubric=tipsc_rubric,
            ethics_rubric=ethics_rubric,
        )
        global tipsc_executor_instance
        tipsc_executor_instance = AsyncPipelineExecutor(stages, db)

        logger.info("[startup] TIPSC Engine initialized (Direct execution) ✓")
        # Architecture note: TIPSC runs as an in-process BackgroundTask, not a Kafka consumer.
        # DFV and Discovery are Kafka-driven (combined_agent_worker.py).
        # Followup answers are handled by the /followup API endpoint, not a Kafka consumer.
    except Exception as exc:
        logger.error("[startup] TIPSC Engine startup failed: %s", exc)

    logger.info("=== AGIS Backend Ready ===")
