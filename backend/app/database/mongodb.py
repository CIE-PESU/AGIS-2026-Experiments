"""
Motor async MongoDB client — connection lifecycle managed here.
Called from events/startup.py and events/shutdown.py.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("MongoDB client not initialised. Call connect_db() first.")
    return _client


async def connect_db() -> None:
    """Initialise Motor client and Beanie ODM. Called on app startup."""
    global _client

    # Import here to avoid circular imports at module load time
    from app.models.user import User
    from app.models.team import Team
    from app.models.session import Session
    from app.models.audit import AuditLog
    from app.models.comment import MentorComment
    from app.models.refresh_token import RefreshToken

    _client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
        minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
        serverSelectionTimeoutMS=5000,
    )

    db = _client[settings.MONGODB_DB_NAME]

    await init_beanie(
        database=db,
        document_models=[User, Team, Session, AuditLog, MentorComment, RefreshToken],
    )
    logger.info("MongoDB connected and Beanie initialized.")


async def disconnect_db() -> None:
    """Close Motor client. Called on app shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB disconnected.")
