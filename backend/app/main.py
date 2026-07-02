"""
main.py — FastAPI application entry point for the AGIS Backend.

Wires together:
  - Application lifespan (startup + shutdown events)
  - CORS middleware (origins from env — never hardcoded)
  - Secure headers middleware
  - Request ID middleware
  - Logging middleware
  - Rate limiting middleware
  - Global exception handlers
  - API v1 router (all feature routes under /api/v1)
  - Health routes at root level (/health, /ready, /live)
  - Internal worker routes (not on public v1 prefix)

Architecture rule: This file only wires things together.
No business logic, no database calls, no service imports here.
"""

from __future__ import annotations

import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

# ─────────────────────────────────────────────────────────────────────────────
# Logging configuration (must be set up before any module-level loggers fire)
# ─────────────────────────────────────────────────────────────────────────────

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "DEBUG" if settings.DEBUG else "INFO",
        "handlers": ["console"],
    },
    "loggers": {
        "agis.access": {"level": "INFO", "propagate": True},
        "uvicorn": {"level": "WARNING", "propagate": True},
        "uvicorn.access": {"level": "WARNING", "propagate": True},
    },
})

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan (replaces deprecated @app.on_event)
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async context manager for app startup and shutdown."""
    from app.events.startup import on_startup
    await on_startup()
    yield
    from app.events.shutdown import on_shutdown
    await on_shutdown()


# ─────────────────────────────────────────────────────────────────────────────
# Application factory
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.

    Separated into a factory function to support testing (test client can
    call create_app() instead of importing `app` directly).
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AGIS Entrepreneurship Coach Platform — Backend API. "
            "Handles session management, flow orchestration via Kafka, "
            "and role-based access control for students, mentors, and admins."
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Exception handlers ─────────────────────────────────────────────────────
    from app.exceptions.handlers import register_exception_handlers
    register_exception_handlers(app)

    # ── Middleware (order: outermost → innermost, i.e. last added = first executed) ──
    # Rate limiting — must run before we do expensive work
    from app.middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

    # Logging — runs after request_id is attached
    from app.middleware.logging import LoggingMiddleware
    app.add_middleware(LoggingMiddleware)

    # Request ID — outermost layer (runs first on the way in)
    from app.middleware.request_id import RequestIDMiddleware
    app.add_middleware(RequestIDMiddleware)

    # CORS — must come after RequestIDMiddleware so preflight requests get request_id too
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,  # From env — never hardcoded
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-API-Version"],
    )

    # ── Secure headers (added as response middleware) ─────────────────────────
    @app.middleware("http")
    async def add_secure_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-API-Version"] = settings.APP_VERSION
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # ── Max request body size (reject bodies over 1MB) ───────────────────────
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    # Body size enforcement via ContentSizeLimitMiddleware or similar
    # Using a simple middleware approach:
    @app.middleware("http")
    async def limit_body_size(request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
            from fastapi.responses import JSONResponse
            from datetime import datetime, timezone
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": f"Request body exceeds the maximum allowed size of {settings.MAX_REQUEST_BODY_BYTES} bytes.",
                        "field": None,
                        "request_id": getattr(request.state, "request_id", "unknown"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
        return await call_next(request)

    # ── Routers ────────────────────────────────────────────────────────────────

    # Health endpoints — available at both root AND /api/v1 (no auth required, no prefix confusion)
    from app.api.v1.health import router as health_router
    app.include_router(health_router)  # /health, /ready, /live

    # Public API v1 (auth, sessions, flows, etc.)
    from app.api.v1 import v1_router
    app.include_router(v1_router, prefix="/api/v1")

    # Internal worker routes — only reachable from internal network (different prefix)
    # Vijay wires these in on Day 2 (B-13)
    # from app.api.internal.worker_updates import router as internal_router
    # app.include_router(internal_router, prefix="/internal")

    logger.info(
        "App created | env=%s | debug=%s | cors_origins=%s",
        settings.ENVIRONMENT,
        settings.DEBUG,
        settings.cors_origins_list,
    )

    return app


# ─────────────────────────────────────────────────────────────────────────────
# Module-level app instance (used by uvicorn: uvicorn app.main:app)
# ─────────────────────────────────────────────────────────────────────────────
app = create_app()
