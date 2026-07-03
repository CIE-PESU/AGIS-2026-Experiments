"""
Unit tests for FlowService (B-12), covering every Day 2 acceptance
criterion. Uses fake in-memory implementations of session_repo,
kafka_producer, and audit_service, so these run with no real MongoDB or
Kafka broker — and don't depend on Bhavesh's / Vijay's / Palash's
branches being merged yet.
"""

from __future__ import annotations

import pytest

from app.services.flow_exceptions import (
    DFVNotUnlockedError,
    FlowAlreadyRunningError,
    InvalidStateTransitionError,
    SessionNotFoundError,
)
from app.services.flow_service import (
    DFV_TOPIC,
    DISCOVERY_TOPIC,
    TIPSC_TOPIC,
    FlowService,
    SessionSnapshot,
)
from app.state_machine.states import SessionStatus


class FakeSessionRepo:
    def __init__(self, sessions: dict[str, SessionSnapshot]):
        self.sessions = sessions
        self.status_updates: list[tuple[str, SessionStatus, int]] = []
        self.dfv_input_writes: list[tuple[str, dict]] = []
        self.fail_version_check = False

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
    return SessionSnapshot(**defaults)


def build_service(session: SessionSnapshot, kafka_fails: bool = False):
    repo = FakeSessionRepo({session.session_id: session})
    kafka = FakeKafkaProducer(should_fail=kafka_fails)
    audit = FakeAuditService()
    return FlowService(repo, kafka, audit), repo, kafka, audit


# ---------------------------------------------------------------------------
# trigger_tipsc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_tipsc_from_created_publishes_and_queues():
    session = make_session(status=SessionStatus.CREATED)
    service, repo, kafka, audit = build_service(session)

    result = await service.trigger_tipsc(session.session_id, session.student_id)

    assert result["status"] == "queued"
    assert result["correlation_id"] is not None
    assert kafka.published[0][0] == TIPSC_TOPIC
    assert kafka.published[0][1]["problem_statement"] == session.problem_statement
    assert repo.status_updates[-1][1] == SessionStatus.QUEUED
    assert audit.events[-1][1] == "TIPSC_TRIGGERED"


@pytest.mark.asyncio
async def test_trigger_tipsc_idempotent_when_already_queued():
    session = make_session(status=SessionStatus.QUEUED)
    service, repo, kafka, audit = build_service(session)

    result = await service.trigger_tipsc(session.session_id, session.student_id)

    assert result["status"] == "queued"
    assert kafka.published == []  # no re-publish
    assert repo.status_updates == []
    assert audit.events == []


@pytest.mark.asyncio
async def test_trigger_tipsc_already_running_returns_flow_already_running():
    session = make_session(status=SessionStatus.TIPSC_RUNNING)
    service, *_ = build_service(session)

    with pytest.raises(FlowAlreadyRunningError):
        await service.trigger_tipsc(session.session_id, session.student_id)


@pytest.mark.asyncio
async def test_trigger_tipsc_wrong_state_returns_invalid_state_transition():
    session = make_session(status=SessionStatus.TIPSC_COMPLETED)
    service, *_ = build_service(session)

    with pytest.raises(InvalidStateTransitionError):
        await service.trigger_tipsc(session.session_id, session.student_id)


@pytest.mark.asyncio
async def test_trigger_tipsc_session_not_found_for_other_student():
    session = make_session(status=SessionStatus.CREATED, student_id="stu_1")
    service, *_ = build_service(session)

    with pytest.raises(SessionNotFoundError):
        await service.trigger_tipsc(session.session_id, "stu_2")


@pytest.mark.asyncio
async def test_trigger_tipsc_kafka_failure_does_not_update_status():
    session = make_session(status=SessionStatus.CREATED)
    service, repo, kafka, audit = build_service(session, kafka_fails=True)

    from app.services.flow_exceptions import KafkaUnavailableError

    with pytest.raises(KafkaUnavailableError):
        await service.trigger_tipsc(session.session_id, session.student_id)

    assert repo.status_updates == []
    assert audit.events == []
    assert session.status == SessionStatus.CREATED  # unchanged


# ---------------------------------------------------------------------------
# trigger_dfv
# ---------------------------------------------------------------------------


VALID_DFV_INPUTS = {
    "desirability_context": "x" * 120,
    "feasibility_context": "y" * 120,
    "viability_context": "z" * 120,
}


@pytest.mark.asyncio
async def test_trigger_dfv_not_unlocked_returns_dfv_not_unlocked():
    session = make_session(
        status=SessionStatus.TIPSC_COMPLETED,
        tipsc={"ready_for_dfv": False, "reasoning": "..."},
    )
    service, *_ = build_service(session)

    with pytest.raises(DFVNotUnlockedError):
        await service.trigger_dfv(session.session_id, session.student_id, VALID_DFV_INPUTS)


@pytest.mark.asyncio
async def test_trigger_dfv_before_tipsc_completed_returns_invalid_state_transition():
    session = make_session(status=SessionStatus.TIPSC_RUNNING)
    service, *_ = build_service(session)

    with pytest.raises(InvalidStateTransitionError):
        await service.trigger_dfv(session.session_id, session.student_id, VALID_DFV_INPUTS)


@pytest.mark.asyncio
async def test_trigger_dfv_happy_path_publishes_and_moves_to_dfv_waiting():
    session = make_session(
        status=SessionStatus.TIPSC_COMPLETED,
        tipsc={"ready_for_dfv": True, "reasoning": "solid idea"},
    )
    service, repo, kafka, audit = build_service(session)

    result = await service.trigger_dfv(session.session_id, session.student_id, VALID_DFV_INPUTS)

    assert result["status"] == "dfv_waiting"
    assert kafka.published[0][0] == DFV_TOPIC
    assert kafka.published[0][1]["desirability_context"] == VALID_DFV_INPUTS["desirability_context"]
    assert repo.dfv_input_writes[-1] == (session.session_id, VALID_DFV_INPUTS)
    assert repo.status_updates[-1][1] == SessionStatus.DFV_WAITING
    assert audit.events[-1][1] == "DFV_TRIGGERED"


@pytest.mark.asyncio
async def test_trigger_dfv_already_running_returns_flow_already_running():
    session = make_session(
        status=SessionStatus.DFV_RUNNING,
        tipsc={"ready_for_dfv": True},
    )
    service, *_ = build_service(session)

    with pytest.raises(FlowAlreadyRunningError):
        await service.trigger_dfv(session.session_id, session.student_id, VALID_DFV_INPUTS)


# ---------------------------------------------------------------------------
# trigger_discovery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_discovery_before_dfv_completed_returns_invalid_state_transition():
    session = make_session(status=SessionStatus.DFV_WAITING)
    service, *_ = build_service(session)

    with pytest.raises(InvalidStateTransitionError):
        await service.trigger_discovery(session.session_id, session.student_id)


@pytest.mark.asyncio
async def test_trigger_discovery_happy_path():
    session = make_session(
        status=SessionStatus.DFV_COMPLETED,
        tipsc={"reasoning": "solid idea"},
        dfv={"summary": "strong market pull"},
    )
    service, repo, kafka, audit = build_service(session)

    result = await service.trigger_discovery(session.session_id, session.student_id)

    assert result["status"] == "discovery_waiting"
    assert kafka.published[0][0] == DISCOVERY_TOPIC
    assert kafka.published[0][1]["tipsc_summary"] == "solid idea"
    assert kafka.published[0][1]["dfv_summary"] == "strong market pull"
    assert repo.status_updates[-1][1] == SessionStatus.DISCOVERY_WAITING
    assert audit.events[-1][1] == "DISCOVERY_TRIGGERED"


# ---------------------------------------------------------------------------
# optimistic lock conflict
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_version_mismatch_raises_conflict():
    session = make_session(status=SessionStatus.CREATED)
    repo = FakeSessionRepo({session.session_id: session})
    repo.fail_version_check = True
    kafka = FakeKafkaProducer()
    audit = FakeAuditService()
    service = FlowService(repo, kafka, audit)

    from app.services.flow_exceptions import SessionUpdateConflictError

    with pytest.raises(SessionUpdateConflictError):
        await service.trigger_tipsc(session.session_id, session.student_id)