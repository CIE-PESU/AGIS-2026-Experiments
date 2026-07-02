"""
middleware/request_id.py — X-Request-ID injection middleware.

For every request:
  - If X-Request-ID header is present: use it (enables client-side tracing)
  - If not: generate a new UUID4
  - Store on request.state.request_id for use in exception handlers and loggers
  - Echo the value in every response as X-Request-ID header

This middleware must be mounted FIRST so request_id is available to all
subsequent middleware and exception handlers.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Injects X-Request-ID into request state and echoes it in every response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Use client-provided ID (for distributed tracing) or generate one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store on request state so handlers and loggers can access it
        request.state.request_id = request_id

        # Process the request
        response: Response = await call_next(request)

        # Always echo the request_id in the response header
        response.headers["X-Request-ID"] = request_id

        return response
