# backend/app/dependencies/worker_auth.py
import logging
from fastapi import Header, HTTPException, status
from app.core.config import settings

logger = logging.getLogger(__name__)

async def verify_worker_secret(
    x_worker_secret: str = Header(..., alias="X-Worker-Secret", description="Internal secret key from the worker pool")
) -> str:
    """
    Validates the internal worker secret header.
    Rejects unauthorized traffic with a 403 INVALID_WORKER_SECRET.
    """
    if x_worker_secret != settings.WORKER_INTERNAL_SECRET:
        logger.warning("Unauthorized worker request blocked. Invalid X-Worker-Secret provided.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="INVALID_WORKER_SECRET"
        )
    return x_worker_secret