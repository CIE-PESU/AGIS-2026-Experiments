import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


logger = logging.getLogger("agis")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every incoming request and outgoing response.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response: Response = await call_next(request)

        process_time = round((time.time() - start_time) * 1000, 2)

        request_id = getattr(request.state, "request_id", "N/A")

        logger.info(
            f"{request.method} {request.url.path} | "
            f"Status={response.status_code} | "
            f"Time={process_time}ms | "
            f"RequestID={request_id}"
        )

        return response