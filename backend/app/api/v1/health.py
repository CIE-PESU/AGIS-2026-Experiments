"""
api/v1/health.py — Health check endpoints.

Three endpoints per standard Kubernetes probe conventions:

  GET /health   — Full health with service dependency status
  GET /ready    — Returns 200 only when all dependencies are ready
  GET /live     — Always returns 200 (process heartbeat)

These endpoints are NOT rate-limited and require no auth.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="System health check",
    description="Returns health status of MongoDB and Kafka producer. Returns 503 if any dependency is down.",
)
async def health_check() -> JSONResponse:
    """
    GET /health

    Checks MongoDB ping and Kafka producer state.
    Returns 200 if healthy, 503 if degraded.
    """
    from app.database.mongodb import ping_db

    mongo_ok = await ping_db()

    # Vijay's Kafka producer health — placeholder until B-06 merges
    kafka_ok = True
    # try:
    #     from app.kafka.producer import kafka_producer
    #     kafka_ok = kafka_producer.is_running
    # except Exception:
    #     kafka_ok = False

    all_healthy = mongo_ok and kafka_ok
    http_status = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content={
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "mongodb": "connected" if mongo_ok else "disconnected",
                "kafka_producer": "connected" if kafka_ok else "disconnected",
            },
        },
    )


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Returns 200 only when the backend is fully initialized and ready to serve traffic.",
)
async def readiness_probe() -> JSONResponse:
    """
    GET /ready

    Used by Kubernetes/load balancer as a readiness probe.
    Returns 200 only when DB is connected and Kafka is ready.
    """
    from app.database.mongodb import ping_db

    mongo_ok = await ping_db()
    kafka_ok = True  # Placeholder until B-06 merges

    if mongo_ok and kafka_ok:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"ready": True, "timestamp": datetime.now(timezone.utc).isoformat()},
        )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "ready": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": "One or more dependencies are not ready.",
        },
    )


@router.get(
    "/live",
    summary="Liveness probe",
    description="Returns 200 as long as the process is running. Used by Kubernetes liveness probe.",
)
async def liveness_probe():
    """
    GET /live

    Always returns 200 if the process can respond to requests.
    No dependency checks — this is a pure process heartbeat.
    """
    return {"alive": True, "timestamp": datetime.now(timezone.utc).isoformat()}
