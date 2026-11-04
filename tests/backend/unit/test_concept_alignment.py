"""Product progress must describe completed reports, not jobs or favorable ratings."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from core.flow_results import completed_flow_output
from models.session import TIPSCRAGScores
from schemas.auth import CurrentUser
from starlette.requests import Request
from state_machine.states import SessionStatus


@pytest.mark.parametrize(
    "flow",
    [
        None,
        {"status": "waiting"},
        {"status": "running", "output": {"old": True}},
        {"status": "failed"},
        {"status": "done", "output": None},
    ],
)
def test_queued_or_incomplete_records_are_not_completed_reports(flow):
    assert completed_flow_output(flow) is None


@pytest.mark.parametrize("state", ["done", "completed"])
def test_completed_output_is_preserved(state):
    assert completed_flow_output({"status": state, "output": {"report": "plan"}}) == {
        "report": "plan"
    }


@pytest.mark.parametrize(
    "status,dfv,discovery,expected_dfv,expected_discovery",
    [
        (SessionStatus.DFV_RUNNING, {"status": "running", "output": None}, None, "Running", False),
        (
            SessionStatus.DISCOVERY_RUNNING,
            {"status": "done", "output": {"decision": "GO"}},
            {"status": "running", "output": None},
            "GO",
            False,
        ),
        (
            SessionStatus.COMPLETED,
            {"status": "done", "output": {"decision": "GO"}},
            {"status": "done", "output": {"report": "plan"}},
            "GO",
            True,
        ),
    ],
)
async def test_team_progress_uses_canonical_scores_and_real_completion(
    monkeypatch, status, dfv, discovery, expected_dfv, expected_discovery
):
    from routes.v1 import sessions

    teammate = SimpleNamespace(id="student-id", srn="STUDENT1", name="Student 1")
    session = SimpleNamespace(
        id="session-id",
        status=status,
        updated_at=datetime.now(UTC),
        tipsc=SimpleNamespace(
            tips_rag_scores=TIPSCRAGScores(
                T="YELLOW",
                IMPORTANT="RED",
                P="GREEN",
                S="YELLOW",
                IMPORTANT_reason="Needs evidence",
            )
        ),
        dfv=dfv,
        discovery=discovery,
    )

    class Query:
        def sort(self, *_):
            return self

        async def first_or_none(self):
            return session

    monkeypatch.setattr(
        sessions,
        "User",
        SimpleNamespace(
            team_id=None,
            role=None,
            find=lambda *_: SimpleNamespace(to_list=AsyncMock(return_value=[teammate])),
        ),
    )
    monkeypatch.setattr(
        sessions,
        "Session",
        SimpleNamespace(student_id=None, status=None, updated_at=0, find=lambda *_: Query()),
    )
    result = await sessions.get_team_progress(
        Request({"type": "http"}),
        CurrentUser(user_id="student-id", role="student", team_id="team-id"),
    )
    row = result["data"][0]
    assert row["tips"]["importance"] == {"status": "red", "explanation": "Needs evidence"}
    assert row["dfv"] == expected_dfv
    assert row["jtbd"] is expected_discovery
