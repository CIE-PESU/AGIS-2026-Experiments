"""
exceptions/handlers.py — FastAPI global exception handlers.

Maps every AppException subclass to the standard error envelope defined
in api-spec.md Section 1.2. Unhandled exceptions return 500 INTERNAL_ERROR
without any stack trace in the response body.
"""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.base import AppException

logger = logging.getLogger(__name__)


def _error_envelope(
    error_code: str,
    message: str,
    request_id: str,
    field: str | None = None,
) -> dict:
    """Build the standard error response envelope (api-spec.md Section 1.2)."""
    return {
        "error": {
            "code": error_code,
            "message": message,
            "field": field,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


def _get_request_id(request: Request) -> str:
    """Extract X-Request-ID injected by the request_id middleware."""
    return getattr(request.state, "request_id", "unknown")


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI application."""

    # ── Typed AppException (our hierarchy) ────────────────────────────────────
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.warning(
            "AppException | %s | %s | request_id=%s",
            exc.error_code,
            exc.message,
            request_id,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content=_error_envelope(
                error_code=exc.error_code,
                message=exc.message,
                request_id=request_id,
                field=exc.field,
            ),
        )

    # ── FastAPI / Starlette HTTPException ──────────────────────────────────────
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = _get_request_id(request)
        # Map common HTTP codes to our catalog codes
        code_map = {
            401: "TOKEN_INVALID",
            403: "INSUFFICIENT_PERMISSIONS",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            429: "RATE_LIMIT_EXCEEDED",
        }
        error_code = code_map.get(exc.status_code, "HTTP_ERROR")
        logger.warning(
            "HTTPException | %d %s | request_id=%s",
            exc.status_code,
            exc.detail,
            request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_envelope(
                error_code=error_code,
                message=str(exc.detail),
                request_id=request_id,
            ),
        )

    # ── Pydantic RequestValidationError (422) ──────────────────────────────────
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = _get_request_id(request)
        errors = exc.errors()
        # Build a human-readable message from the first error
        first = errors[0] if errors else {}
        field = ".".join(str(loc) for loc in first.get("loc", []) if loc != "body")
        message = first.get("msg", "Validation error")
        logger.info(
            "ValidationError | %s | request_id=%s | errors=%s",
            field,
            request_id,
            errors,
        )
        return JSONResponse(
            status_code=422,
            content=_error_envelope(
                error_code="VALIDATION_ERROR",
                message=f"{field}: {message}" if field else message,
                request_id=request_id,
                field=field or None,
            ),
        )

    # ── Catch-all: unhandled exceptions ───────────────────────────────────────
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _get_request_id(request)
        # Log full traceback internally — NEVER send it to the client.
        logger.error(
            "UNHANDLED_EXCEPTION | %s | request_id=%s\n%s",
            type(exc).__name__,
            request_id,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content=_error_envelope(
                error_code="INTERNAL_ERROR",
                message="An unexpected error occurred. Please contact support with your request_id.",
                request_id=request_id,
            ),
        )
