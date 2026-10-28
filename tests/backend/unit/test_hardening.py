"""Security and delivery regressions requiring no real services."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from core.security import hash_password, verify_password
from auth.jwt import create_access_token, decode_token, create_refresh_token, verify_refresh_token
from exceptions.base import TokenInvalidError
from middleware.body_size import BodySizeLimitMiddleware
from workers.combined_agent_worker import CombinedAgentWorker, DeliveryError


def test_passwords_are_salted_and_not_recoverable():
    password = "long-password-" * 20
    first, second = hash_password(password), hash_password(password)
    assert first != second and password not in first
    assert verify_password(password, first)
    assert not verify_password(password + "wrong", first)
    assert not verify_password(password, "corrupt")


def test_tokens_require_expiration_and_signature():
    import jwt
    from core.config import settings
    token = create_access_token("user", "student", "User", workspace_id="workspace")
    assert decode_token(token)["workspace_id"] == "workspace"
    unsigned_expiry = jwt.encode({"sub": "user"}, settings.JWT_SECRET, algorithm="HS256")
    with pytest.raises(TokenInvalidError):
        decode_token(unsigned_expiry)
    raw, digest = create_refresh_token()
    assert raw != digest and verify_refresh_token(raw, digest)
    assert not verify_refresh_token("wrong", digest)


@pytest.mark.parametrize("headers,chunks,expected", [
    ([], [b"123", b"456"], 413),
    ([(b"content-length", b"bad")], [], 400),
    ([], [b"123"], 200),
])
async def test_body_limits_measure_streamed_bytes(headers, chunks, expected):
    from starlette.responses import Response
    async def app(scope, receive, send):
        await Response("ok")(scope, receive, send)
    messages = [{"type": "http.request", "body": chunk, "more_body": i < len(chunks)-1} for i, chunk in enumerate(chunks)]
    sent = []
    await BodySizeLimitMiddleware(app, 5)(
        {"type": "http", "method": "POST", "headers": headers},
        AsyncMock(side_effect=messages), AsyncMock(side_effect=sent.append))
    assert sent[0]["status"] == expected


async def test_result_survives_worker_restart_and_backend_outage(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKER_DELIVERY_DB", str(tmp_path / "deliveries.db"))
    worker = CombinedAgentWorker()
    attempts = []
    def offline(request):
        attempts.append(request)
        return httpx.Response(503, json={"error": {"code": "UNAVAILABLE"}})
    worker.http_client = httpx.AsyncClient(transport=httpx.MockTransport(offline), base_url="http://backend")
    body = {"status": "done", "output": {"decision": "GO"}}
    with pytest.raises(DeliveryError):
        await worker._report_success(session_id="507f1f77bcf86cd799439011", flow="dfv", correlation_id="run", output=body, duration_seconds=1)
    await worker.http_client.aclose()
    restarted = CombinedAgentWorker()
    def online(request):
        import json
        assert json.loads(request.content)["output"] == body
        return httpx.Response(200, json={"status": "success"})
    restarted.http_client = httpx.AsyncClient(transport=httpx.MockTransport(online), base_url="http://backend")
    restarted._process_dfv = AsyncMock()
    await restarted._handle_dfv({"userSession_id": "507f1f77bcf86cd799439011", "correlation_id": "run", "payload": {}})
    restarted._process_dfv.assert_not_awaited()
    await restarted.http_client.aclose()


async def test_transient_version_conflict_retains_delivery(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKER_DELIVERY_DB", str(tmp_path / "deliveries.db"))
    worker = CombinedAgentWorker()
    worker.http_client = httpx.AsyncClient(base_url="http://backend", transport=httpx.MockTransport(
        lambda _: httpx.Response(409, json={"error": {"code": "SESSION_VERSION_CONFLICT"}})))
    with pytest.raises(DeliveryError):
        await worker._report_failure(session_id="507f1f77bcf86cd799439011", flow="dfv", correlation_id="run",
            error_code="FAIL", error_message="Failed", retry_count=0)
    await worker.http_client.aclose()


async def test_consumer_never_commits_before_delivery():
    worker = CombinedAgentWorker()
    processed = []
    class Consumer:
        def __aiter__(self):
            async def messages():
                yield SimpleNamespace(value={"job": 1}, topic="userSession.dfv", partition=0, offset=3)
            return messages()
        def assignment(self): return set()
        def pause(self, *partitions): pass
        def resume(self, *partitions): pass
        async def getmany(self, **kwargs): return {}
        async def commit(self, offsets):
            assert processed == [1]
            assert list(offsets.values()) == [4]
    async def handler(value):
        processed.append(value["job"])
    await worker._consume(Consumer(), handler)


async def test_no_go_discovery_is_rejected():
    from tests.backend.unit.test_flow_service import make_session, build_service, VALID_DISCOVERY_INPUTS
    from services.flow_exceptions import InvalidStateTransitionError
    from state_machine.states import SessionStatus
    service = build_service(make_session(status=SessionStatus.DFV_COMPLETED, dfv={"output": {"final_decision": {"status": "NO-GO"}}}))
    with pytest.raises(InvalidStateTransitionError):
        await service.trigger_discovery("ses_1", "stu_1", VALID_DISCOVERY_INPUTS)


async def test_kafka_probe_checks_broker_instead_of_started_flag(monkeypatch):
    from kafka.producer import kafka_producer
    metadata = AsyncMock(side_effect=OSError("Broker offline"))
    monkeypatch.setattr(kafka_producer, "_producer", SimpleNamespace(client=SimpleNamespace(fetch_all_metadata=metadata)))
    monkeypatch.setattr(kafka_producer, "is_running", True)
    assert not await kafka_producer.check_health()
    metadata.side_effect = None
    assert await kafka_producer.check_health()
