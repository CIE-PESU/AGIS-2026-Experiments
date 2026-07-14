import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import BackgroundTasks

from exceptions.session import (
    SessionNotFoundError,
    InvalidStateTransitionError,
)
from exceptions.base import (
    CorrelationIDMismatchError,
    InvalidOutputSchemaError,
)
from models.session import SessionStatus
from services.worker_service import WorkerService

class FakeSessionSnapshot:
    def __init__(self, **kwargs):
        self.id = "ses_1"
        self.correlation_id = "corr_1"
        self.status = SessionStatus.TIPSC_RUNNING
        self.version = 1
        for k, v in kwargs.items():
            setattr(self, k, v)

class FakeSessionRepo:
    def __init__(self, session=None):
        self.session = session or FakeSessionSnapshot()
        self.update_flow_output_called_with = None
        self.update_flow_failure_called_with = None

    async def find_by_id(self, session_id):
        if self.session and self.session.id == session_id:
            return self.session
        return None

    async def update_flow_output(self, session_id, flow, output, new_status, expected_version):
        self.update_flow_output_called_with = (session_id, flow, output, new_status, expected_version)
        if self.session:
            self.session.status = new_status
            self.session.version += 1
        return True

    async def update_flow_failure(self, session_id, new_status, failure_metadata):
        self.update_flow_failure_called_with = (session_id, new_status, failure_metadata)
        if self.session:
            self.session.status = new_status
            self.session.version += 1
        return True

@pytest.fixture
def worker_service(monkeypatch):
    service = WorkerService()
    repo = FakeSessionRepo()
    monkeypatch.setattr("services.worker_service.session_repo", repo)
    monkeypatch.setattr("services.worker_service.audit_service", AsyncMock())
    return service, repo

@pytest.mark.asyncio
async def test_accept_flow_output_empty_returns_invalid_schema(worker_service):
    service, repo = worker_service
    bg_tasks = BackgroundTasks()
    
    with pytest.raises(InvalidOutputSchemaError) as exc_info:
        await service.accept_flow_output(
            session_id="ses_1",
            flow="tipsc",
            correlation_id="corr_1",
            output={},
            duration_seconds=10.0,
            worker_id="worker_1",
            background_tasks=bg_tasks,
        )
    assert "Output cannot be empty" in str(exc_info.value.message)

@pytest.mark.asyncio
async def test_accept_flow_output_wrong_correlation_id(worker_service):
    service, repo = worker_service
    bg_tasks = BackgroundTasks()
    
    with pytest.raises(CorrelationIDMismatchError):
        await service.accept_flow_output(
            session_id="ses_1",
            flow="tipsc",
            correlation_id="wrong_corr",
            output={"score": {}},
            duration_seconds=10.0,
            worker_id="worker_1",
            background_tasks=bg_tasks,
        )

@pytest.mark.asyncio
async def test_accept_flow_output_terminal_session(worker_service):
    service, repo = worker_service
    repo.session.status = SessionStatus.COMPLETED
    bg_tasks = BackgroundTasks()
    
    with pytest.raises(InvalidStateTransitionError):
        await service.accept_flow_output(
            session_id="ses_1",
            flow="tipsc",
            correlation_id="corr_1",
            output={"score": {}},
            duration_seconds=10.0,
            worker_id="worker_1",
            background_tasks=bg_tasks,
        )

@pytest.mark.asyncio
async def test_valid_tipsc_output_writes_and_sets_status(worker_service):
    service, repo = worker_service
    bg_tasks = BackgroundTasks()
    
    valid_tipsc = {
        "score": {"timing": 1, "idea": 1, "problem": 1, "solution": 1, "competition": 1},
        "total_score": 5,
        "ready_for_dfv": True,
        "compliance_flag": False,
        "reasoning": "Looks good"
    }
    
    res = await service.accept_flow_output(
        session_id="ses_1",
        flow="tipsc",
        correlation_id="corr_1",
        output=valid_tipsc,
        duration_seconds=10.0,
        worker_id="worker_1",
        background_tasks=bg_tasks,
    )
    
    assert res["status"] == "success"
    assert repo.update_flow_output_called_with[1] == "tipsc"
    assert repo.update_flow_output_called_with[3] == SessionStatus.TIPSC_COMPLETED

@pytest.mark.asyncio
async def test_valid_dfv_output_writes_and_sets_status(worker_service):
    service, repo = worker_service
    repo.session.status = SessionStatus.DFV_RUNNING
    bg_tasks = BackgroundTasks()
    
    valid_dfv = {
        "desirability": {"score": 5, "report": "ok"},
        "feasibility": {"score": 5, "report": "ok"},
        "viability": {"score": 5, "report": "ok"},
        "overall_decision": "GO",
        "summary": "good"
    }
    
    res = await service.accept_flow_output(
        session_id="ses_1",
        flow="dfv",
        correlation_id="corr_1",
        output=valid_dfv,
        duration_seconds=10.0,
        worker_id="worker_1",
        background_tasks=bg_tasks,
    )
    
    assert res["status"] == "success"
    assert repo.update_flow_output_called_with[1] == "dfv"
    assert repo.update_flow_output_called_with[3] == SessionStatus.DFV_COMPLETED

@pytest.mark.asyncio
async def test_valid_discovery_output_writes_and_sets_status(worker_service):
    service, repo = worker_service
    repo.session.status = SessionStatus.DISCOVERY_RUNNING
    bg_tasks = BackgroundTasks()
    
    valid_discovery = {
        "interview_plan": {
            "target_segment": "Students",
            "hypothesis_to_validate": "They need this."
        }
    }
    
    res = await service.accept_flow_output(
        session_id="ses_1",
        flow="discovery",
        correlation_id="corr_1",
        output=valid_discovery,
        duration_seconds=10.0,
        worker_id="worker_1",
        background_tasks=bg_tasks,
    )
    
    assert res["status"] == "success"
    assert repo.update_flow_output_called_with[1] == "discovery"
    assert repo.update_flow_output_called_with[3] == SessionStatus.COMPLETED

@pytest.mark.asyncio
async def test_accept_flow_failure(worker_service):
    service, repo = worker_service
    bg_tasks = BackgroundTasks()
    
    res = await service.accept_flow_failure(
        session_id="ses_1",
        flow="tipsc",
        correlation_id="corr_1",
        error_code="TIMEOUT",
        error_message="Worker timeout",
        retry_count=1,
        background_tasks=bg_tasks,
    )
    
    assert res["status"] == "success"
    assert repo.update_flow_failure_called_with[1] == SessionStatus.TIPSC_FAILED
    assert repo.update_flow_failure_called_with[2]["error_code"] == "TIMEOUT"
