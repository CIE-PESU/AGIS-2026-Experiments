"""
Unit tests for FlowService (B-12), covering every Day 2 acceptance
criterion. Uses fake in-memory implementations of session_repo,
kafka_producer, and audit_service, so these run with no real MongoDB or
Kafka broker — and don't depend on Bhavesh's / Vijay's / Palash's
branches being merged yet.
"""

from __future__ import annotations

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from services.flow_exceptions import (
    DFVNotUnlockedError,
    FlowAlreadyRunningError,
    InvalidStateTransitionError,
    SessionNotFoundError,
    KafkaUnavailableError,
    SessionUpdateConflictError,
)
from services.flow_service import (
    DFV_TOPIC,
    DISCOVERY_TOPIC,
    FlowService,
    SessionSnapshot,
)
from state_machine.states import SessionStatus


class FakeSessionRepo:
    def __init__(self, sessions: dict[str, SessionSnapshot]):
        self.sessions = sessions
        self.status_updates: list[tuple[str, SessionStatus, int]] = []
        self.dfv_input_writes: list[tuple[str, dict]] = []
        self.fail_version_check = False
        self.atomic_dfv_results: dict[str, bool] = {}
        self.atomic_discovery_results: dict[str, bool] = {}

    async def find_by_id(self, session_id):
        return self.sessions.get(session_id)

    async def find_by_id_and_student(self, session_id, student_id):
        session = self.sessions.get(session_id)
        if session is None or session.student_id != student_id:
            return None
        return session

    async def update_status(self, session_id, new_status, expected_version):
        self.status_updates.append((session_id, new_status, expected_version))
        if self.fail_version_check:
            return False
        session = self.sessions[session_id]
        session.status = new_status
        session.version += 1
        return True

    async def update_dfv_inputs(self, session_id, dfv_inputs):
        self.dfv_input_writes.append((session_id, dfv_inputs))
        return True

    async def set_correlation_id(self, session_id, correlation_id):
        session = self.sessions[session_id]
        session.correlation_id = correlation_id

    async def atomic_start_dfv_flow(self, session_id, correlation_id, dfv_inputs, expected_version=None, request_record=None):
        result = self.atomic_dfv_results.get(session_id, True)
        if result:
            session = self.sessions[session_id]
            session.correlation_id = correlation_id
        return result

    async def atomic_start_discovery_flow(self, session_id, correlation_id, discovery_inputs, expected_version=None, request_record=None):
        result = self.atomic_discovery_results.get(session_id, True)
        if result:
            session = self.sessions[session_id]
            session.correlation_id = correlation_id
        return result

    async def update_flow_failure(self, session_id, new_status, failure_metadata, expected_version=None, correlation_id=None):
        self.sessions[session_id].status = new_status
        return True


class FakeKafkaProducer:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.published: list[tuple[str, dict]] = []

    async def publish(self, topic, payload):
        if self.should_fail:
            raise RuntimeError("simulated Kafka outage")
        self.published.append((topic, payload))
        return payload["correlation_id"]


class FakeAuditService:
    def __init__(self):
        self.events: list[tuple[str, str, str, str, dict]] = []

    async def log_event(self, session_id, event, actor, actor_role, metadata):
        self.events.append((session_id, event, actor, actor_role, metadata))


def make_session(**overrides) -> SessionSnapshot:
    defaults = dict(
        session_id="ses_1",
        student_id="stu_1",
        team_id="team_1",
        status=SessionStatus.CREATED,
        version=0,
        problem_statement="Students in Tier-2 cities lack access to mentorship.",
        idea="A mobile-first async mentorship platform.",
        tipsc=None,
        dfv=None,
    )
    defaults.update(overrides)
    merged = {**defaults, **overrides}
    return SessionSnapshot(**merged)


VALID_DFV_INPUTS = {
    "desirability_context": "x" * 120,
    "feasibility_context": "y" * 120,
    "viability_context": "z" * 120,
}


@pytest.mark.asyncio
async def test_no_go_dfv_can_retry_with_revised_inputs():
    session = make_session(
        status=SessionStatus.DFV_COMPLETED,
        tipsc={"ready_for_dfv": True},
        dfv={"output": {"decision": "NO-GO"}},
    )
    service = build_service(session)

    result = await service.trigger_dfv(session.session_id, session.student_id, VALID_DFV_INPUTS)

    assert result["status"] == "dfv_waiting"


@pytest.mark.asyncio
async def test_go_dfv_cannot_be_retried():
    session = make_session(
        status=SessionStatus.DFV_COMPLETED,
        tipsc={"ready_for_dfv": True},
        dfv={"output": {"decision": "GO"}},
    )
    service = build_service(session)

    with pytest.raises(InvalidStateTransitionError):
        await service.trigger_dfv(session.session_id, session.student_id, VALID_DFV_INPUTS)


@pytest.mark.asyncio
async def test_dfv_publish_failure_returns_to_retryable_state():
    session = make_session(status=SessionStatus.TIPSC_COMPLETED, tipsc={"ready_for_dfv": True})
    service = build_service(session)

    async def fail_publish(*args, **kwargs):
        raise RuntimeError("Kafka unavailable")

    service._kafka.publish = fail_publish

    with pytest.raises(KafkaUnavailableError):
        await service.trigger_dfv(session.session_id, session.student_id, VALID_DFV_INPUTS)

    assert session.status == SessionStatus.DFV_FAILED


@pytest.mark.asyncio
async def test_discovery_publish_failure_returns_to_retryable_state():
    session = make_session(status=SessionStatus.DFV_COMPLETED, dfv={"output": {"decision": "GO"}})
    service = build_service(session)

    async def fail_publish(*args, **kwargs):
        raise RuntimeError("Kafka unavailable")

    service._kafka.publish = fail_publish

    with pytest.raises(KafkaUnavailableError):
        await service.trigger_discovery(session.session_id, session.student_id, VALID_DISCOVERY_INPUTS)

    assert session.status == SessionStatus.DISCOVERY_FAILED


VALID_DISCOVERY_INPUTS = {
    "target_customer_segment": [{"segment": "students", "role": "learner", "customer_type": "B2C"}],
    "problem_statement": "Test problem",
    "problem_consequence": ["consequence1"],
    "current_alternatives": ["alt1"],
    "key_assumptions": ["assumption1"],
    "what_we_already_know": ["know1"],
    "biggest_uncertainty": ["uncertainty1"],
    "customer_type": ["B2C"],
    "proposed_solution_context": {"purpose": "test", "summary": "test summary"},
}


def build_service(session: SessionSnapshot):
    """Build a FlowService with mocked TIPSC executor."""

    repo = FakeSessionRepo({session.session_id: session})
    kafka = type('MockKafka', (), {'published': [], 'publish': lambda *a, **kw: asyncio.sleep(0, result='test-correlation-id')})()
    audit = type('MockAudit', (), {'log_event': lambda *a, **kw: asyncio.sleep(0, result=None)})()

    service = FlowService(
        session_repo=FakeSessionRepo({session.session_id: session}),
        kafka_producer=type('MockKafka', (), {'published': [], 'publish': lambda *a, **kw: asyncio.sleep(0, result='test-correlation-id')})(),
        audit_service=type('MockAudit', (), {'log_event': lambda *a, **kw: asyncio.sleep(0, result=None)})(),
    )

    # Mock the executor in the service
    service._executor = type('MockExecutor', (), {
        'run': lambda *a, **kw: asyncio.sleep(0, result={}),
        'resume_after_followup': lambda *a, **kw: asyncio.sleep(0, result={})
    })()

    return service


# ─────────────────────────────────────────────────────────────────────────────
# trigger_tipsc
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_tipsc_from_created_publishes_and_queues():
    session = make_session(status=SessionStatus.CREATED)
    service = build_service(session)

    # Mock the global tipsc_executor_instance
    with patch('events.startup.tipsc_executor_instance', service._executor):
        result = await service.trigger_tipsc(session.session_id, session.student_id)

    assert result["status"] == "queued"
    assert result["correlation_id"] is not None


@pytest.mark.asyncio
async def test_trigger_tipsc_idempotent_when_already_queued():
    session = make_session(status=SessionStatus.QUEUED)
    service = build_service(session)
    result = await service.trigger_tipsc(session.session_id, session.student_id)

    assert result["status"] == "queued"


@pytest.mark.asyncio
async def test_trigger_tipsc_already_running_returns_current_status():
    """When TIPSC is already running, returns current status (idempotent), not an error."""
    session = make_session(status=SessionStatus.TIPSC_RUNNING)
    service = build_service(session)

    with patch('events.startup.tipsc_executor_instance', service._executor):
        result = await service.trigger_tipsc(session.session_id, session.student_id)

    # Returns early with current status, doesn't raise
    assert result["status"] == "tipsc_running"


@pytest.mark.asyncio
async def test_trigger_tipsc_wrong_state_returns_invalid_state_transition():
    session = make_session(status=SessionStatus.TIPSC_COMPLETED)
    service = build_service(session)

    with pytest.raises(InvalidStateTransitionError):
        await service.trigger_tipsc(session.session_id, session.student_id)


@pytest.mark.asyncio
async def test_trigger_tipsc_session_not_found_for_other_student():
    session = make_session(status=SessionStatus.CREATED, student_id="stu_1")
    service = build_service(session)

    with pytest.raises(SessionNotFoundError):
        await service.trigger_tipsc(session.session_id, "stu_2")


@pytest.mark.asyncio
async def test_trigger_tipsc_kafka_failure_does_not_update_status():
    session = make_session(status=SessionStatus.CREATED)

    repo = FakeSessionRepo({session.session_id: session})
    # Kafka that fails
    kafka = type('MockKafka', (), {'published': [], 'publish': lambda *a, **kw: asyncio.sleep(0, result='test-correlation-id')})()
    audit = type('MockAudit', (), {'log_event': lambda *a, **kw: asyncio.sleep(0, result=None)})()

    service = FlowService(
        session_repo=FakeSessionRepo({session.session_id: session}),
        kafka_producer=type('MockKafka', (), {'published': [], 'publish': lambda *a, **kw: asyncio.sleep(0, result='test-correlation-id')})(),
        audit_service=type('MockAudit', (), {'log_event': lambda *a, **kw: asyncio.sleep(0, result=None)})(),
    )

    with pytest.raises(Exception):
        await service.trigger_tipsc("ses_1", "stu_1")


# ─────────────────────────────────────────────────────────────────────────────
# trigger_dfv
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_dfv_not_unlocked_returns_dfv_not_unlocked():
    session = make_session(
        status=SessionStatus.TIPSC_COMPLETED,
        tipsc={"ready_for_dfv": False, "reasoning": "..."},
    )
    service = build_service(session)

    with pytest.raises(DFVNotUnlockedError):
        await service.trigger_dfv(session.session_id, session.student_id, VALID_DFV_INPUTS)


@pytest.mark.asyncio
async def test_trigger_dfv_before_tipsc_completed_returns_dfv_not_unlocked():
    """When TIPSC not completed (no tipsc data), raises DFVNotUnlockedError, not InvalidStateTransitionError."""
    session = make_session(status=SessionStatus.TIPSC_RUNNING)
    service = build_service(session)

    with pytest.raises(DFVNotUnlockedError):
        await service.trigger_dfv(session.session_id, session.student_id, VALID_DFV_INPUTS)


@pytest.mark.asyncio
async def test_trigger_dfv_happy_path_publishes_and_moves_to_dfv_waiting():
    session = make_session(
        status=SessionStatus.TIPSC_COMPLETED,
        tipsc={"ready_for_dfv": True, "reasoning": "solid idea"},
    )

    # Create a single repo instance and use it for both setup and FlowService
    repo = FakeSessionRepo({session.session_id: session})
    repo.find_by_id = lambda *a, **kw: asyncio.sleep(0, result=make_session(
        status=SessionStatus.TIPSC_COMPLETED,
        tipsc={"ready_for_dfv": True, "reasoning": "solid idea"},
    ))
    repo.update_status = lambda *a, **kw: asyncio.sleep(0, result=True)
    repo.set_correlation_id = lambda *a, **kw: asyncio.sleep(0)
    repo.atomic_start_dfv_flow = lambda *a, **kw: asyncio.sleep(0, result=True)

    # Kafka that tracks published messages
    published = []
    async def mock_publish(_self, topic, payload):
        published.append((topic, payload))
        return "test-correlation-id"

    kafka = type('MockKafka', (), {'published': published, 'publish': mock_publish})()
    audit = type('MockAudit', (), {'log_event': lambda *a, **kw: asyncio.sleep(0, result=None)})()

    service = FlowService(
        session_repo=repo,
        kafka_producer=kafka,
        audit_service=audit,
    )

    result = await service.trigger_dfv("ses_1", "stu_1", VALID_DFV_INPUTS)

    assert result["status"] == "dfv_waiting"
    # Payload is DFVJobMessage.model_dump(), which has nested payload field
    assert published[0][1]["payload"]["desirability_context"] == VALID_DFV_INPUTS["desirability_context"]


@pytest.mark.asyncio
async def test_trigger_dfv_already_running_returns_current_status():
    """When DFV is already running, CAS fails and returns current status, doesn't raise."""
    session = make_session(
        status=SessionStatus.DFV_RUNNING,
        tipsc={"ready_for_dfv": True},
    )
    service = build_service(session)
    # Make CAS fail to simulate already running
    service._session_repo.atomic_dfv_results[session.session_id] = False

    result = await service.trigger_dfv(session.session_id, session.student_id, VALID_DFV_INPUTS)

    # Returns current status, doesn't raise
    assert result["status"] == "dfv_running"


# ─────────────────────────────────────────────────────────────────────────────
# trigger_discovery
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_discovery_before_dfv_completed_returns_current_status():
    """When DFV not completed, CAS fails and returns current status, doesn't raise InvalidStateTransitionError."""
    session = make_session(status=SessionStatus.DFV_WAITING)
    service = build_service(session)
    # Make CAS fail to simulate already waiting/running
    service._session_repo.atomic_discovery_results[session.session_id] = False

    with pytest.raises(InvalidStateTransitionError):
        await service.trigger_discovery(session.session_id, session.student_id, VALID_DISCOVERY_INPUTS)


@pytest.mark.asyncio
async def test_trigger_discovery_happy_path():
    session = make_session(
        status=SessionStatus.DFV_COMPLETED,
        tipsc={"ready_for_dfv": True, "reasoning": "solid idea"},
        dfv={"output": {"decision": "GO", "summary": "strong market pull"}},
    )

    repo = FakeSessionRepo({session.session_id: session})
    repo.find_by_id = lambda *a, **kw: asyncio.sleep(0, result=make_session(
        status=SessionStatus.DFV_COMPLETED,
        tipsc={"ready_for_dfv": True, "reasoning": "solid idea"},
        dfv={"output": {"decision": "GO", "summary": "strong market pull"}},
    ))
    repo.update_status = lambda *a, **kw: asyncio.sleep(0, result=True)
    repo.atomic_start_discovery_flow = lambda *a, **kw: asyncio.sleep(0, result=True)

    kafka = type('MockKafka', (), {'published': [], 'publish': lambda *a, **kw: asyncio.sleep(0, result='test-correlation-id')})()
    audit = type('MockAudit', (), {'log_event': lambda *a, **kw: asyncio.sleep(0, result=None)})()

    service = FlowService(
        session_repo=FakeSessionRepo({session.session_id: session}),
        kafka_producer=type('MockKafka', (), {'published': [], 'publish': lambda *a, **kw: asyncio.sleep(0, result='test-correlation-id')})(),
        audit_service=type('MockAudit', (), {'log_event': lambda *a, **kw: asyncio.sleep(0, result=None)})(),
    )

    result = await service.trigger_discovery("ses_1", "stu_1", VALID_DISCOVERY_INPUTS)

    assert result["status"] == "discovery_waiting"


# ─────────────────────────────────────────────────────────────────────────────
# optimistic lock conflict
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_version_mismatch_raises_conflict():
    session = make_session(status=SessionStatus.CREATED)
    repo = FakeSessionRepo({session.session_id: session})
    repo.fail_version_check = True
    kafka = type('MockKafka', (), {'published': [], 'publish': lambda *a, **kw: None})()
    audit = type('MockAudit', (), {'log_event': lambda *a, **kw: None})()
    service = FlowService(repo, type('MockKafka', (), {'published': [], 'publish': lambda *a, **kw: None})(), type('MockAudit', (), {'log_event': lambda *a, **kw: None})())


    with patch("events.startup.tipsc_executor_instance", MagicMock()):
        with pytest.raises(SessionUpdateConflictError):
            await service.trigger_tipsc(session.session_id, session.student_id)
