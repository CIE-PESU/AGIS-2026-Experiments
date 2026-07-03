import time
from collections import defaultdict

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter.

    Allows:
        100 requests per minute per client IP.
    """

    RATE_LIMIT = 100
    WINDOW_SECONDS = 60

    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        current_time = time.time()

        # Remove expired timestamps
        self.requests[client_ip] = [
            timestamp
            for timestamp in self.requests[client_ip]
            if current_time - timestamp < self.WINDOW_SECONDS
        ]

        # Check rate limit
        if len(self.requests[client_ip]) >= self.RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later."
                    }
                },
            )

        # Record current request
        self.requests[client_ip].append(current_time)

        response = await call_next(request)

        return response