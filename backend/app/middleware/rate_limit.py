"""
middleware/rate_limit.py — In-memory sliding window rate limiter.

Two rate limit buckets:
  1. LOGIN — per source IP  (5 req/min by default, see settings.RATE_LIMIT_LOGIN_PER_MINUTE)
  2. API   — per user_id   (60 req/min by default, see settings.RATE_LIMIT_API_PER_MINUTE)

Implementation:
  - Sliding window using a deque of request timestamps per key.
  - Stored in-memory — resets on server restart. Acceptable for this scale.
  - For multi-instance deployments: replace with Redis-backed limiter.

Returns 429 RATE_LIMIT_EXCEEDED on breach with Retry-After header.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

logger = logging.getLogger(__name__)

# Stores: key → deque of request timestamps (float, epoch seconds)
_login_windows: dict[str, deque] = defaultdict(deque)
_api_windows: dict[str, deque] = defaultdict(deque)

_WINDOW_SECONDS = 60  # 1-minute sliding window


def _is_rate_limited(window: dict[str, deque], key: str, limit: int) -> bool:
    """
    Check if the given key has exceeded `limit` requests in the last 60 seconds.

    Cleans up stale entries as it checks (amortized O(n) over window size).
    Returns True if the request should be rejected.
    """
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS
    dq = window[key]

    # Remove expired timestamps from the front
    while dq and dq[0] < cutoff:
        dq.popleft()

    if len(dq) >= limit:
        return True

    dq.append(now)
    return False


def _rate_limit_error(retry_after: int = 60) -> JSONResponse:
    """Build the standard 429 response."""
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(retry_after)},
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please wait before retrying.",
                "field": None,
                "request_id": "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        },
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Applies sliding window rate limiting to login and API endpoints.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # ── Login rate limit (per IP) ──────────────────────────────────────────
        if path.endswith("/auth/login"):
            client_ip = request.client.host if request.client else "unknown"
            if _is_rate_limited(_login_windows, client_ip, settings.RATE_LIMIT_LOGIN_PER_MINUTE):
                logger.warning("Login rate limit exceeded for IP=%s", client_ip)
                return _rate_limit_error()

        # ── General API rate limit (per user_id from JWT) ──────────────────────
        elif path.startswith("/api/"):
            from app.auth.jwt import decode_token

            user_id: str | None = None
            try:
                auth = request.headers.get("Authorization", "")
                if auth.startswith("Bearer "):
                    payload = decode_token(auth[7:])
                    user_id = payload.get("sub")
            except Exception:
                pass  # Unauthenticated requests: rate limit by IP instead

            limit_key = user_id or (request.client.host if request.client else "unknown")
            if _is_rate_limited(_api_windows, limit_key, settings.RATE_LIMIT_API_PER_MINUTE):
                logger.warning("API rate limit exceeded for key=%s", limit_key)
                return _rate_limit_error()

        return await call_next(request)
