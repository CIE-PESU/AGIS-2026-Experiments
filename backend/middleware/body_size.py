"""Bound actual request bytes, including chunked requests without Content-Length."""

from datetime import UTC, datetime

from starlette.responses import JSONResponse


class BodySizeLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        length = headers.get(b"content-length")
        status = None
        if length is not None:
            try:
                if int(length) < 0:
                    status = 400
                elif int(length) > self.max_bytes:
                    status = 413
            except ValueError:
                status = 400
        messages = []
        size = 0
        while status is None:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.max_bytes:
                status = 413
                break
            if not message.get("more_body", False):
                break
        if status:
            response = JSONResponse(
                status_code=status,
                content={
                    "error": {
                        "code": "PAYLOAD_TOO_LARGE" if status == 413 else "INVALID_CONTENT_LENGTH",
                        "message": "Request body exceeds limit"
                        if status == 413
                        else "Invalid Content-Length",
                        "field": None,
                        "request_id": scope.get("state", {}).get("request_id", "unknown"),
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                },
            )
            return await response(scope, receive, send)
        iterator = iter(messages)

        async def replay():
            return next(iterator, None) or await receive()

        await self.app(scope, replay, send)
