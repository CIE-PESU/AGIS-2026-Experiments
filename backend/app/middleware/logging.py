"""
middleware/logging.py — Structured request/response logging middleware.

Logs every HTTP request with:
  - Method + path
  - user_id (extracted from JWT if available — never from DB)
  - Status code
  - Response time in milliseconds
  - X-Request-ID

Sensitive field masking:
  Any field named password, token, secret, or key in the request body is
  NEVER logged. This is a hard rule — never relax it.
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.auth.jwt import decode_token
from app.core.config import settings

logger = logging.getLogger("agis.access")

# Fields that must NEVER appear in logs
_SENSITIVE_FIELDS = frozenset({"password", "token", "secret", "key", "token_hash"})


def _extract_user_id(request: Request) -> str:
    """
    Attempt to extract user_id from the Authorization JWT for logging.
    Returns "anonymous" if no token or token is invalid.
    Never raises — logging must not break the request.
    """
    try:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            payload = decode_token(auth[7:])
            return payload.get("sub", "anonymous")
    except Exception:
        pass
    return "anonymous"


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every request and response in a structured format.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_ns = time.perf_counter_ns()

        user_id = _extract_user_id(request)
        request_id = getattr(request.state, "request_id", "unknown")

        response: Response = await call_next(request)

        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000

        logger.info(
            "method=%s path=%s status=%d user_id=%s request_id=%s duration_ms=%.1f",
            request.method,
            request.url.path,
            response.status_code,
            user_id,
            request_id,
            elapsed_ms,
        )

        return response
