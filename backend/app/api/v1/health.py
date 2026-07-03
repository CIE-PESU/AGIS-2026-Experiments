from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(
    prefix="",
    tags=["Health"],
)


@router.get("/health")
async def health():
    """
    Overall health status of the backend.
    """
    return {
        "status": "healthy",
        "service": "AGIS Backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness():
    """
    Readiness probe.
    """
    return {
        "status": "ready",
        "checks": {
            "application": "ready"
        },
    }


@router.get("/live")
async def liveness():
    """
    Liveness probe.
    """
    return {
        "status": "alive",
    }