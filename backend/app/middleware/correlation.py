"""
middleware/correlation.py — X-Correlation-ID propagation middleware.

X-Correlation-ID is used for distributed tracing across services (backend → Kafka → workers).
If a client provides X-Correlation-ID, we echo it on every response.
If not provided, we generate one from the request_id.

This is distinct from X-Request-ID:
  - X-Request-ID: unique per HTTP request into this service
  - X-Correlation-ID: traces a logical operation across multiple services
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Propagates X-Correlation-ID across the distributed system.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Use client-provided correlation ID or fall back to request ID
        correlation_id = (
            request.headers.get("X-Correlation-ID")
            or getattr(request.state, "request_id", None)
            or str(uuid.uuid4())
        )

        request.state.correlation_id = correlation_id

        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id

        return response
