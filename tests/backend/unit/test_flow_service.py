"""Current DFV handoff behavior with in-memory collaborators."""

from types import SimpleNamespace
import pytest

from services.flow_exceptions import DFVNotUnlockedError, KafkaUnavailableError, SessionNotFoundError
from services.flow_service import DFV_TOPIC, FlowService
from state_machine.states import SessionStatus


class Repo:
    def __init__(self, session):
        self.session, self.started, self.failures = session, [], []

    async def find_by_id(self, session_id):
        return self.session if session_id == self.session.id else None

    async def atomic_start_flow(self, *args):
        self.started.append(args)
        self.session.status = SessionStatus.DFV_WAITING
        self.session.correlation_id = args[2]
        self.session.version += 1
        return True

    async def update_flow_failure(self, *args, **kwargs):
        self.failures.append((args, kwargs))
        self.session.status = SessionStatus.DFV_FAILED
        return True


class Producer:
    def __init__(self, fail=False):
        self.fail, self.messages = fail, []

    async def publish(self, topic, payload):
        if self.fail:
            raise RuntimeError("Kafka unavailable")
        self.messages.append((topic, payload))
        return payload["correlation_id"]


class Audit:
    def __init__(self):
        self.events = []

    async def log_event(self, **kwargs):
        self.events.append(kwargs)


def make_service(*, ready=True, producer_fails=False):
    session = SimpleNamespace(
        id="session-1", student_id="student-1", workspace_id=None,
        team_id="team-1", status=SessionStatus.TIPSC_COMPLETED, version=1,
        tipsc={"ready_for_dfv": ready}, dfv=None, discovery=None,
        idea="A reservation app", problem_statement="Queues are too long",
        correlation_id=None, flow_requests={},
    )
    repo, producer, audit = Repo(session), Producer(producer_fails), Audit()
    return FlowService(repo, producer, audit), repo, producer, audit


INPUTS = {
    "desirability_context": "Students wait in queues before classes and need their stationery immediately. " * 2,
    "feasibility_context": "The shop can reserve stock using its existing staff and a simple mobile web page. " * 2,
    "viability_context": "The shop pays a subscription after it sees enough additional sales to justify the cost. " * 2,
}


@pytest.mark.asyncio
async def test_dfv_trigger_records_job_and_publishes():
    service, repo, producer, audit = make_service()
    result = await service.trigger_dfv("session-1", "student-1", INPUTS)
    assert result["status"] == "dfv_waiting"
    assert repo.started and repo.started[0][0:2] == ("session-1", "dfv")
    assert producer.messages[0][0] == DFV_TOPIC
    assert producer.messages[0][1]["correlation_id"] == result["correlation_id"]
    assert audit.events[0]["event"] == "DFV_TRIGGERED"


@pytest.mark.asyncio
async def test_completed_session_can_start_fresh_dfv_run():
    service, repo, producer, _ = make_service()
    repo.session.status = SessionStatus.COMPLETED
    result = await service.trigger_dfv("session-1", "student-1", INPUTS)
    assert result["status"] == "dfv_waiting"
    assert producer.messages[0][0] == DFV_TOPIC


@pytest.mark.asyncio
async def test_dfv_requires_matching_owner_and_tipsc_clearance():
    service, repo, producer, _ = make_service(ready=False)
    with pytest.raises(SessionNotFoundError):
        await service.trigger_dfv("session-1", "another-student", INPUTS)
    with pytest.raises(DFVNotUnlockedError):
        await service.trigger_dfv("session-1", "student-1", INPUTS)
    assert not repo.started and not producer.messages


@pytest.mark.asyncio
async def test_kafka_failure_moves_dfv_out_of_waiting():
    service, repo, _, _ = make_service(producer_fails=True)
    with pytest.raises(KafkaUnavailableError):
        await service.trigger_dfv("session-1", "student-1", INPUTS)
    assert repo.failures
    assert repo.session.status == SessionStatus.DFV_FAILED


@pytest.mark.asyncio
async def test_tipsc_retry_does_not_queue_without_executor(monkeypatch):
    from events import startup
    service, repo, _, _ = make_service()
    repo.session.status = SessionStatus.TIPSC_FAILED
    monkeypatch.setattr(startup, "tipsc_executor_instance", None)
    with pytest.raises(RuntimeError, match="TIPSC executor is not initialized"):
        await service.trigger_tipsc("session-1", "student-1")
    assert repo.session.status == SessionStatus.TIPSC_FAILED
