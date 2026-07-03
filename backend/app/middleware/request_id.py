import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to attach a unique request ID to every request.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id

        response: Response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        return response