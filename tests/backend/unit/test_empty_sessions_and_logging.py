"""Expected empty states stay successful and repeated fallback notices stay bounded."""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from core.logging_filters import ApproximateTokenCountFilter, configure_agent_log_filters
from schemas.auth import CurrentUser
from starlette.requests import Request


@pytest.mark.parametrize("role", ["student", "mentor_workspace"])
async def test_no_active_session_is_a_successful_empty_state(monkeypatch, role):
    from routes.v1 import sessions

    repo = SimpleNamespace(
        find_active_by_student=AsyncMock(return_value=None),
        find_active_by_owner=AsyncMock(return_value=None),
    )
    monkeypatch.setattr(sessions, "session_repo", repo)
    caller = CurrentUser(
        user_id="owner", role=role, workspace_id="workspace" if role == "mentor_workspace" else None
    )
    response = await sessions.get_active_session_by_user(Request({"type": "http"}), "owner", caller)
    assert response["data"] is None


def record(message, *args):
    return logging.LogRecord("crewai.llms.base_llm", logging.WARNING, "", 0, message, args, None)


def test_only_duplicate_token_estimation_notices_are_filtered():
    notice = "Using an approximate input token count for model %r: assuming one token per four characters because a native token count is unavailable."
    filter_ = ApproximateTokenCountFilter()
    assert filter_.filter(record(notice, "model-a"))
    assert not filter_.filter(record(notice, "model-a"))
    assert filter_.filter(record(notice, "model-b"))
    for message in [
        "Provider authentication failed",
        "Request timed out",
        "Context window exceeded",
    ]:
        assert filter_.filter(record(message))
        assert filter_.filter(record(message))


def test_filter_configuration_is_idempotent():
    configure_agent_log_filters()
    configure_agent_log_filters()
    assert (
        sum(
            isinstance(item, ApproximateTokenCountFilter)
            for item in logging.getLogger("crewai.llms.base_llm").filters
        )
        == 1
    )
