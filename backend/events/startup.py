"""
events/startup.py

Application startup handler.

Initializes:
    1. MongoDB + Beanie
    2. Database indexes
    3. Kafka producer
    4. In-process TIPSC engine
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import yaml


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# TIPSC source path
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TIPSC_SRC_DIR = (
    PROJECT_ROOT
    / "TIPSC-Agent"
    / "src"
)

TIPSC_SRC_PATH = str(TIPSC_SRC_DIR)


# TIPSC uses absolute imports such as:
#
#     from models import PreEvalOutput
#     from engine.dispatcher import WorkerDispatcher
#
# Therefore TIPSC/src must be resolved before backend modules.
if TIPSC_SRC_PATH not in sys.path:
    sys.path.insert(0, TIPSC_SRC_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# Global engine instances
# ─────────────────────────────────────────────────────────────────────────────

tipsc_executor_instance = None


def _load_yaml(relative_path: str) -> dict:
    """
    Load a TIPSC YAML configuration file.
    """

    path = TIPSC_SRC_DIR / relative_path

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return yaml.safe_load(file)


def _load_text(relative_path: str) -> str:
    """
    Load a TIPSC text/skill file.
    """

    path = TIPSC_SRC_DIR / relative_path

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return file.read()


async def on_startup() -> None:
    """
    FastAPI lifespan startup handler.

    Startup order matters:

        MongoDB
        -> Indexes
        -> Kafka
        -> TIPSC Engine
    """

    global tipsc_executor_instance

    logger.info(
        "=== AGIS Backend Starting Up ==="
    )

    # ──────────────────────────────────────────────────────────────────────
    # 1. MongoDB
    # ──────────────────────────────────────────────────────────────────────

    try:

        from database.mongodb import connect_db

        await connect_db()

        logger.info(
            "[startup] MongoDB"
        )

    except Exception as exc:

        logger.critical(
            "[startup] MongoDB connection FAILED: %s",
            exc,
        )

        raise

    # ──────────────────────────────────────────────────────────────────────
    # 2. Database indexes
    # ──────────────────────────────────────────────────────────────────────

    try:

        from database.indexes import create_indexes

        await create_indexes()

        logger.info(
            "[startup] Indexes"
        )

    except Exception as exc:

        logger.error(
            "[startup] Index creation failed "
            "(non-fatal): %s",
            exc,
        )

    # ──────────────────────────────────────────────────────────────────────
    # 3. Kafka producer
    # ──────────────────────────────────────────────────────────────────────

    try:

        from kafka.producer import kafka_producer

        await kafka_producer.start()

        logger.info(
            "[startup] Kafka Producer"
        )

    except Exception as exc:

        logger.warning(
            "[startup] Kafka Producer unavailable "
            "(non-fatal): %s",
            exc,
        )

    # ──────────────────────────────────────────────────────────────────────
    # 4. TIPSC engine
    # ──────────────────────────────────────────────────────────────────────

    try:

        from core.config import settings
        from database.mongodb import get_client

        from engine.async_pipeline_executor import (
            AsyncPipelineExecutor,
        )
        from engine.db import SessionStore
        from engine.stages import PipelineStages

        # ── Mongo collection ───────────────────────────────────────────────

        client = get_client()

        mongo_database = client[
            settings.MONGODB_DB_NAME
        ]

        sessions_collection = mongo_database[
            "sessions"
        ]

        session_store = SessionStore(
            sessions_collection
        )

        # ── TIPSC configuration ────────────────────────────────────────────

        agents_cfg = _load_yaml(
            "config/agents.yaml"
        )

        task_cfg = _load_yaml(
            "config/tasks.yaml"
        )

        preeval_skill = _load_text(
            "skills/preeval/SKILL.md"
        )

        tipsc_rubric = _load_text(
            "skills/tipsc/SKILL.md"
        )

        ethics_rubric = _load_text(
            "skills/ethics/SKILL.md"
        )

        # ── LLM ───────────────────────────────────────────────────────────

        try:

            from crewai import LLM

            llm = LLM(
            model=settings.OPENAI_MODEL_NAME,
            base_url=settings.LM_STUDIO_URL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.2,
            )  

            logger.info(
                "[startup] TIPSC LLM initialized | "
                "model=%s",
                os.getenv(
                    "OPENAI_MODEL_NAME",
                    (
                        "lmstudio-community/"
                        "Meta-Llama-3-8B-Instruct-GGUF"
                    ),
                ),
            )

        except Exception as exc:

            logger.exception(
                "[startup] Failed to initialize "
                "TIPSC LLM: %s",
                exc,
            )

            raise

        # ── Pipeline stages ────────────────────────────────────────────────

        stages = PipelineStages(
            llm=llm,
            agents_cfg=agents_cfg,
            task_cfg=task_cfg,
            preeval_skill=preeval_skill,
            tipsc_rubric=tipsc_rubric,
            ethics_rubric=ethics_rubric,
        )

        # ── Executor ───────────────────────────────────────────────────────

        tipsc_executor_instance = (
            AsyncPipelineExecutor(
                stages=stages,
                db=session_store,
            )
        )

        logger.info(
            "[startup] TIPSC Engine initialized "
            "(direct execution)"
        )

    except Exception as exc:

        tipsc_executor_instance = None

        logger.exception(
            "[startup] TIPSC Engine startup failed: %s",
            exc,
        )

    try:
        from services.timeout_supervisor import timeout_supervisor
        timeout_supervisor.start(check_interval_seconds=60)
        logger.info("[startup] Timeout supervisor background task started OK")
    except Exception as exc:
        logger.error("[startup] Failed to start timeout supervisor: %s", exc)

    logger.info(
        "=== AGIS Backend Ready ==="
    )