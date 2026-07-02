"""
database/mongodb.py — Motor async MongoDB client initialization and Beanie ODM setup.

- Singleton Motor client
- Beanie initialized with all document models
- Connection pool: configurable via settings (default 10 connections)
- connect_db() called from events/startup.py
- disconnect_db() called from events/shutdown.py
"""

from __future__ import annotations

import logging

import motor.motor_asyncio
from beanie import init_beanie

from app.core.config import settings

logger = logging.getLogger(__name__)

# Singleton Motor client — do NOT re-create per request.
_motor_client: motor.motor_asyncio.AsyncIOMotorClient | None = None


def get_motor_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    """Return the initialized Motor client. Raises if not connected."""
    if _motor_client is None:
        raise RuntimeError("MongoDB client is not initialized. Call connect_db() first.")
    return _motor_client


async def connect_db() -> None:
    """
    Initialize the Motor client and Beanie ODM.

    Called once on application startup. Registers all Beanie document models
    so that Beanie can resolve collection names and run validation.
    """
    global _motor_client

    # Import all models here to avoid circular imports at module level.
    # Every Beanie model used anywhere in the app must be listed here.
    from app.models.refresh_token import RefreshToken
    from app.models.user import User

    # Day 1 models — Bhavesh will add his models here when his branch is ready
    # from app.models.session import Session
    # from app.models.team import Team
    # from app.models.audit import AuditLog
    # from app.models.comment import Comment

    logger.info("Connecting to MongoDB at %s (db: %s) ...", settings.MONGODB_URI[:30], settings.MONGODB_DB_NAME)

    _motor_client = motor.motor_asyncio.AsyncIOMotorClient(
        settings.MONGODB_URI,
        maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
        minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
        serverSelectionTimeoutMS=5000,
    )

    database = _motor_client[settings.MONGODB_DB_NAME]

    await init_beanie(
        database=database,
        document_models=[
            User,
            RefreshToken,
            # Add more models as other branches merge in
        ],
    )

    logger.info("MongoDB connected and Beanie initialized.")


async def disconnect_db() -> None:
    """
    Close the Motor client connection pool.

    Called on application shutdown.
    """
    global _motor_client

    if _motor_client is not None:
        _motor_client.close()
        _motor_client = None
        logger.info("MongoDB connection closed.")


async def ping_db() -> bool:
    """
    Perform a lightweight ping to check MongoDB reachability.

    Returns True on success, False if the DB is unreachable.
    Used by the /health endpoint.
    """
    try:
        client = get_motor_client()
        await client.admin.command("ping")
        return True
    except Exception as exc:
        logger.warning("MongoDB ping failed: %s", exc)
        return False
