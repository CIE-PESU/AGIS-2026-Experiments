"""Deletion must remove only sessions owned by the caller and never running work."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from exceptions.base import InsufficientPermissionsError
from schemas.auth import CurrentUser
from services.session_service import SessionService
from state_machine.states import SessionStatus


@pytest.mark.asyncio
async def test_owner_can_delete_completed_session(monkeypatch):
    repo = SimpleNamespace(
        find_by_id=AsyncMock(return_value=SimpleNamespace(
            student_id="owner", workspace_id=None, status=SessionStatus.COMPLETED,
        )),
        delete_by_id=AsyncMock(return_value=True),
    )
    monkeypatch.setattr("services.session_service.session_repo", repo)
    service = SessionService()
    service.get_session = AsyncMock()

    await service.delete_session("session-1", CurrentUser(user_id="owner", role="student"))

    repo.delete_by_id.assert_awaited_once_with("session-1")


@pytest.mark.asyncio
async def test_teammate_cannot_delete_another_students_session(monkeypatch):
    repo = SimpleNamespace(
        find_by_id=AsyncMock(return_value=SimpleNamespace(
            student_id="owner", workspace_id=None, status=SessionStatus.COMPLETED,
        )),
        delete_by_id=AsyncMock(),
    )
    monkeypatch.setattr("services.session_service.session_repo", repo)
    service = SessionService()
    service.get_session = AsyncMock()  # Teammates may read a session.

    with pytest.raises(InsufficientPermissionsError):
        await service.delete_session("session-1", CurrentUser(user_id="teammate", role="student"))

    repo.delete_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_running_session_can_be_deleted(monkeypatch):
    repo = SimpleNamespace(
        find_by_id=AsyncMock(return_value=SimpleNamespace(
            student_id="owner", workspace_id=None, status=SessionStatus.QUEUED,
        )),
        delete_by_id=AsyncMock(return_value=True),
    )
    monkeypatch.setattr("services.session_service.session_repo", repo)
    service = SessionService()
    service.get_session = AsyncMock()

    await service.delete_session("session-1", CurrentUser(user_id="owner", role="student"))

    repo.delete_by_id.assert_awaited_once_with("session-1")
