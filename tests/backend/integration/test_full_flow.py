"""Real MongoDB/Kafka, real API/pipeline, deterministic agent outputs; no paid calls."""
import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from aiokafka import AIOKafkaConsumer
from pydantic import BaseModel, ConfigDict

pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    os.getenv("AGIS_INTEGRATION") != "1", reason="Set AGIS_INTEGRATION=1 and start the isolated test stack")]


class Output(BaseModel):
    model_config = ConfigDict(extra="allow")


INTAKE = dict(problem_statement="Students lack affordable access to expert mentorship in their region.",
    customer_segment="University students in smaller cities seeking business mentorship.",
    consequence="Students cannot validate ideas and spend money on weak businesses.",
    assumptions=["Students will use a remote mentor"], proposed_solution="An affordable remote mentorship platform connecting students and experts.",
    target_geography="India", industry_sector="Education")
DFV = {k: "Relevant evidence and market context. " * 5 for k in
       ["desirability_context", "feasibility_context", "viability_context"]}
DISCOVERY = dict(target_customer_segment=[dict(segment="students", role="learner", customer_type="B2C")],
    problem_statement=INTAKE["problem_statement"], problem_consequence=["Lost time"],
    current_alternatives=["Friends"], key_assumptions=["Will pay"], what_we_already_know=["Need help"],
    biggest_uncertainty=["Willingness to pay"], customer_type=["B2C"],
    proposed_solution_context=dict(purpose="Mentorship", summary=INTAKE["proposed_solution"]))


@pytest.fixture
async def stack(monkeypatch, tmp_path):
    from core.config import settings
    from database.mongodb import connect_db, disconnect_db, get_client
    from kafka.producer import kafka_producer
    from events import startup
    from backend.main import create_app
    from engine.async_pipeline_executor import AsyncPipelineExecutor
    from engine.db import SessionStore
    from tipsc_models import PreEvalOutput
    from services.session_task_registry import stop_session_tasks
    monkeypatch.setattr(settings, "MONGODB_DB_NAME", "agis_test_" + uuid.uuid4().hex)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_PER_MINUTE", 10000)
    monkeypatch.setenv("WORKER_DELIVERY_DB", str(tmp_path / "deliveries.sqlite3"))
    await connect_db()
    from database.indexes import create_indexes
    await create_indexes()
    await kafka_producer.start()
    executor = AsyncPipelineExecutor(SimpleNamespace(execute_compliance_context=lambda *_: "No restrictions"),
        SessionStore(get_client()[settings.MONGODB_DB_NAME]["sessions"]))
    tipsc = Output(ready_for_dfv=True, needs_followup=False, overall_readiness="STRONG",
        solution_alignment="GREEN", tips_rag_scores={k: "GREEN" for k in "TIPS"}, refined_idea={})
    executor.dispatcher = SimpleNamespace(
        dispatch_preeval=AsyncMock(side_effect=lambda data: PreEvalOutput(**data)),
        dispatch_validation=AsyncMock(return_value=Output(validation_summary="STRONG")),
        dispatch_regulatory=AsyncMock(return_value=Output(regulatory_summary="No restriction")),
        dispatch_ethics=AsyncMock(return_value=Output(ethics_pass=True, compliance_flag=False)),
        dispatch_tipsc=AsyncMock(return_value=tipsc), dispatch_tipsc_reeval=AsyncMock(return_value=tipsc),
        dispatch_followup=AsyncMock(return_value=Output(needs_followup=True, questions=["What evidence supports willingness to pay?"])))
    monkeypatch.setattr(startup, "tipsc_executor_instance", executor)
    app = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield SimpleNamespace(client=client, executor=executor, tipsc=tipsc, app=app)
    await stop_session_tasks()
    await kafka_producer.stop()
    await get_client().drop_database(settings.MONGODB_DB_NAME)
    await disconnect_db()


async def login(stack, srn="PES2UG22CS001", role="student"):
    from models.user import User
    from core.security import hash_password
    await User(srn=srn, name="Test User", role=role, password_hash=hash_password("test-password-123")).insert()
    response = await stack.client.post("/api/v1/auth/login", json={"srn": srn, "password": "test-password-123"})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    return {"Authorization": "Bearer " + data["access_token"]}, data


async def create(stack, headers):
    response = await stack.client.post("/api/v1/sessions", json=INTAKE,
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 201, response.text
    return response.json()["data"]["session_id"]


async def wait_status(stack, session_id, headers, status):
    for _ in range(100):
        response = await stack.client.get(f"/api/v1/sessions/{session_id}", headers=headers)
        assert response.status_code == 200, response.text
        if response.json()["data"]["status"] == status:
            return response.json()["data"]
        await asyncio.sleep(.02)
    raise AssertionError(response.text)


async def consume_one(topic, trigger):
    from core.config import settings
    consumer = AIOKafkaConsumer(topic, bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="test-" + uuid.uuid4().hex, auto_offset_reset="latest", enable_auto_commit=False)
    await consumer.start()
    try:
        # Wait for the group assignment, then publish.
        for _ in range(50):
            await consumer.getmany(timeout_ms=100)
            if consumer.assignment():
                break
        response = await trigger()
        assert response.status_code == 202, response.text
        message = await asyncio.wait_for(consumer.getone(), 15)
        import json
        return json.loads(message.value), response.json()["data"]
    finally:
        await consumer.stop()


async def callback(stack, session_id, flow, correlation_id, output):
    from core.config import settings
    response = await stack.client.post(f"/internal/sessions/{session_id}/output", json={
        "flow": flow, "correlation_id": correlation_id, "output": {"status": "done", "output": output},
        "duration_seconds": 1, "worker_id": "integration"}, headers={"X-Worker-Secret": settings.WORKER_INTERNAL_SECRET})
    assert response.status_code == 200, response.text


async def test_tipsc_to_dfv_to_discovery(stack):
    headers, tokens = await login(stack)
    session_id = await create(stack, headers)
    await wait_status(stack, session_id, headers, "tipsc_completed")
    refreshed = await stack.client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200, refreshed.text
    from auth.jwt import decode_token
    assert decode_token(refreshed.json()["data"]["access_token"])["workspace_id"] == decode_token(tokens["access_token"])["workspace_id"]
    key = str(uuid.uuid4())
    job, result = await consume_one("userSession.dfv", lambda: stack.client.post(
        f"/api/v1/sessions/{session_id}/trigger/dfv", json=DFV, headers={**headers, "Idempotency-Key": key}))
    assert job["correlation_id"] == result["correlation_id"]
    await callback(stack, session_id, "dfv", job["correlation_id"], {"final_decision": {"status": "GO"}})
    # Late timeout must not overwrite a completed flow.
    from repositories.session_repo import session_repo
    from state_machine.states import SessionStatus
    assert not await session_repo.update_flow_failure(session_id, SessionStatus.DFV_FAILED, {"flow": "dfv"}, correlation_id=job["correlation_id"])
    replay = await stack.client.post(f"/api/v1/sessions/{session_id}/trigger/dfv", json=DFV,
        headers={**headers, "Idempotency-Key": key})
    assert replay.status_code == 202 and replay.json()["data"]["correlation_id"] == job["correlation_id"]
    job, _ = await consume_one("userSession.discovery", lambda: stack.client.post(
        f"/api/v1/sessions/{session_id}/trigger/discovery", json=DISCOVERY, headers=headers))
    await callback(stack, session_id, "discovery", job["correlation_id"], {"report": "Interview guide"})
    await wait_status(stack, session_id, headers, "completed")


async def test_followup_claim_is_atomic(stack):
    stack.tipsc.needs_followup = True
    headers, _ = await login(stack)
    session_id = await create(stack, headers)
    await wait_status(stack, session_id, headers, "waiting_for_founder")
    stack.executor.dispatcher.dispatch_tipsc_reeval.return_value = stack.tipsc.model_copy(update={"needs_followup": False})
    responses = await asyncio.gather(*[stack.client.post(f"/api/v1/sessions/{session_id}/followup",
        json={"answer": "We interviewed twenty paying customers and confirmed demand."}, headers=headers) for _ in range(2)])
    assert sorted(r.status_code for r in responses) == [202, 409]
    doc = await wait_status(stack, session_id, headers, "tipsc_completed")
    assert len(doc["followup_history"]) == 1


async def test_cross_owner_idempotency_and_no_go(stack):
    headers, _ = await login(stack)
    session_id = await create(stack, headers)
    await wait_status(stack, session_id, headers, "tipsc_completed")
    job, _ = await consume_one("userSession.dfv", lambda: stack.client.post(
        f"/api/v1/sessions/{session_id}/trigger/dfv", json=DFV, headers=headers))
    other, _ = await login(stack, "PES2UG22CS002")
    denied = await stack.client.post(f"/api/v1/sessions/{session_id}/trigger/dfv", json=DFV,
        headers={**other, "Idempotency-Key": str(uuid.uuid4())})
    assert denied.status_code == 404, denied.text
    await callback(stack, session_id, "dfv", job["correlation_id"], {"final_decision": {"status": "NO-GO"}})
    blocked = await stack.client.post(f"/api/v1/sessions/{session_id}/trigger/discovery", json=DISCOVERY, headers=headers)
    assert blocked.status_code == 409, blocked.text


async def test_refresh_rotation_has_one_winner(stack):
    _, tokens = await login(stack)
    responses = await asyncio.gather(*[stack.client.post("/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}) for _ in range(2)])
    assert sorted(r.status_code for r in responses) == [200, 401]


async def test_workspace_revocation_and_stale_pipeline_write(stack):
    from services.workspace_service import workspace_service
    from engine.db import SessionStore
    from database.mongodb import get_client
    from core.config import settings
    raw, _ = await workspace_service.create_magic_link_workspace("Isolated", "test-admin")
    access = await workspace_service.redeem_magic_link(raw)
    headers = {"Authorization": "Bearer " + access.access_token}
    session_id = await create(stack, headers)
    await wait_status(stack, session_id, headers, "tipsc_completed")
    store = SessionStore(get_client()[settings.MONGODB_DB_NAME]["sessions"])
    await store.get_session(session_id)
    with pytest.raises(RuntimeError):
        await store.update_session(session_id, {"status": "tipsc_running"})
    from fastapi import BackgroundTasks
    tasks = BackgroundTasks()
    await workspace_service.revoke_workspace(access.workspace_id, tasks)
    # Access is denied immediately, before asynchronous deletion.
    denied = await stack.client.get(f"/api/v1/sessions/{session_id}/stream", headers=headers)
    assert denied.status_code == 401, denied.text
    await tasks()
    from repositories.session_repo import session_repo
    assert await session_repo.find_by_id(session_id) is None


async def test_real_application_startup_and_readiness(monkeypatch):
    from core.config import settings
    from backend.main import create_app
    from database.mongodb import get_client
    from events import startup
    monkeypatch.setattr(settings, "MONGODB_DB_NAME", "agis_test_" + uuid.uuid4().hex)
    monkeypatch.setattr(startup, "tipsc_executor_instance", None)
    app = create_app()
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            ready = await client.get("/api/v1/ready")
            assert ready.status_code == 200, ready.text
            health = await client.get("/api/v1/health")
            assert health.json()["services"]["kafka_producer"] == "connected"
        info = await get_client()[settings.MONGODB_DB_NAME]["refresh_tokens"].index_information()
        assert any(i.get("expireAfterSeconds") == 0 for i in info.values())
        assert any(i.get("unique") for i in info.values())
        await get_client().drop_database(settings.MONGODB_DB_NAME)


async def test_simultaneous_session_creation_has_one_record(stack):
    headers, _ = await login(stack)
    key = str(uuid.uuid4())
    responses = await asyncio.gather(*[stack.client.post("/api/v1/sessions", json=INTAKE,
        headers={**headers, "Idempotency-Key": key}) for _ in range(2)])
    assert all(r.status_code == 201 for r in responses), [r.text for r in responses]
    assert len({r.json()["data"]["session_id"] for r in responses}) == 1
    from models.session import Session
    assert await Session.find_all().count() == 1


async def test_abandoned_tipsc_becomes_retryable(stack):
    from models.session import Session
    from services.timeout_supervisor import TimeoutSupervisor
    session = Session(student_id="orphan", problem_statement="Test", idea="Test",
        status="tipsc_running", correlation_id="old-run", updated_at=datetime.now(UTC) - timedelta(hours=2))
    await session.insert()
    await TimeoutSupervisor().check_and_recover_stuck_sessions(timeout_seconds=1800)
    recovered = await Session.get(session.id)
    assert recovered.status.value == "tipsc_failed"
    assert recovered.failure_metadata.error_code == "TIPSC_TIMEOUT"


async def test_quickstart_uses_canonical_agent_contract(stack, monkeypatch):
    from quickstart_agent.models import QuickstartInput, QuickstartOutput, ParameterRating
    from typing import get_args
    headers, _ = await login(stack)
    payload = {name: "Non-sensitive sample founder context" for name in QuickstartInput.model_fields}
    output = QuickstartOutput.from_raw(QuickstartInput(**payload), [
        {"name": name, "rating": "GREEN", "reason": "Supported by test evidence"}
        for name in get_args(ParameterRating.model_fields["name"].annotation)
    ], {}, [])
    monkeypatch.setattr("quickstart_agent.main.run_quickstart_eval_async", AsyncMock(return_value=output))
    response = await stack.client.post("/api/v1/quickstart/evaluate", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["green_count"] == 10
    assert len(response.json()["data"]["parameters"]) == 10
    bad = await stack.client.post("/api/v1/quickstart/evaluate", headers=headers, json={**payload, "problem": "   "})
    assert bad.status_code == 422
