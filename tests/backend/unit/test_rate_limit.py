"""App factories isolate rate-limit history while retaining request throttling."""

import httpx
import pytest
from core.config import settings
from fastapi import FastAPI
from middleware.rate_limit import RateLimitMiddleware


def make_app():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.post("/api/v1/auth/login")
    @app.post("/api/v1/example")
    async def endpoint():
        return {"ok": True}

    return app


@pytest.mark.parametrize(
    "path,setting",
    [
        ("/api/v1/auth/login", "RATE_LIMIT_LOGIN_PER_MINUTE"),
        ("/api/v1/example", "RATE_LIMIT_API_PER_MINUTE"),
    ],
)
async def test_requests_are_throttled_per_application(monkeypatch, path, setting):
    monkeypatch.setattr(settings, setting, 2)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=make_app()), base_url="http://test"
    ) as client:
        assert (await client.post(path)).status_code == 200
        assert (await client.post(path)).status_code == 200
        limited = await client.post(path)
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert limited.headers["Retry-After"] == "60"
    # A fresh application cannot inherit the preceding app's request history.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=make_app()), base_url="http://test"
    ) as client:
        assert (await client.post(path)).status_code == 200
