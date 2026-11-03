"""Archive requires management permission and cannot clobber a newer pipeline run."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from exceptions.base import CannotArchiveActiveSessionError, InsufficientPermissionsError
from fastapi import BackgroundTasks
from schemas.auth import CurrentUser
from services.flow_exceptions import SessionUpdateConflictError
from services.session_service import SessionService
from state_machine.states import RUNNING_STATES, SessionStatus


@pytest.fixture
def archive_setup(monkeypatch):
    session = SimpleNamespace(
        id="507f1f77bcf86cd799439011",
        student_id="owner",
        workspace_id=None,
        status=SessionStatus.TIPSC_COMPLETED,
        version=4,
    )
    repo = SimpleNamespace(
        find_by_id=AsyncMock(return_value=session), archive=AsyncMock(return_value=True)
    )
    monkeypatch.setattr("services.session_service.session_repo", repo)
    service = SessionService()
    service.get_session = AsyncMock()
    return session, repo, service


@pytest.mark.parametrize(
    "caller",
    [
        CurrentUser(user_id="teammate", role="student"),
        CurrentUser(user_id="mentor", role="mentor"),
        CurrentUser(user_id="workspace", role="mentor_workspace"),
    ],
)
async def test_read_access_does_not_grant_archive_permission(archive_setup, caller):
    session, repo, service = archive_setup
    with pytest.raises(InsufficientPermissionsError):
        await service.archive_session(session.id, caller, BackgroundTasks())
    repo.archive.assert_not_awaited()


@pytest.mark.parametrize("state", sorted(RUNNING_STATES, key=lambda item: item.value))
async def test_running_session_cannot_be_archived(archive_setup, state):
    session, repo, service = archive_setup
    session.status = state
    with pytest.raises(CannotArchiveActiveSessionError):
        await service.archive_session(
            session.id, CurrentUser(user_id="owner", role="student"), BackgroundTasks()
        )
    repo.archive.assert_not_awaited()


async def test_archive_conflict_is_retryable_and_does_not_cancel_work(archive_setup, monkeypatch):
    session, repo, service = archive_setup
    repo.archive.return_value = False
    cancel = MagicMock()
    monkeypatch.setattr("services.session_service.cancel_session_task", cancel)
    with pytest.raises(SessionUpdateConflictError):
        await service.archive_session(
            session.id, CurrentUser(user_id="owner", role="student"), BackgroundTasks()
        )
    repo.archive.assert_awaited_once_with(session.id, expected_version=4)
    cancel.assert_not_called()


async def test_owner_archive_cancels_parked_task_and_returns_current_document(
    archive_setup, monkeypatch
):
    session, repo, service = archive_setup
    session.status = SessionStatus.WAITING_FOR_FOUNDER
    cancel = MagicMock()
    response = MagicMock()
    monkeypatch.setattr("services.session_service.cancel_session_task", cancel)
    monkeypatch.setattr("services.session_service.SessionResponse.from_document", response)
    tasks = BackgroundTasks()
    result = await service.archive_session(
        session.id, CurrentUser(user_id="owner", role="student"), tasks
    )
    assert result is response.return_value
    response.assert_called_once_with(session)
    cancel.assert_called_once_with(session.id)
    assert len(tasks.tasks) == 1


async def test_repository_archive_matches_version_and_idle_state(monkeypatch):
    from models.session import Session
    from repositories.session_repo import session_repo

    query = MagicMock(update=AsyncMock(return_value=SimpleNamespace(modified_count=1)))
    find = MagicMock(return_value=query)
    monkeypatch.setattr(Session, "find_one", find)
    assert await session_repo.archive("507f1f77bcf86cd799439011", expected_version=9)
    predicate = find.call_args.args[0]
    assert predicate["version"] == 9
    assert set(predicate["status"]["$nin"]) == {s.value for s in RUNNING_STATES}
    assert predicate["archived_at"] is None
    update = query.update.await_args.args[0]
    assert update["$set"]["status"] == "archived"
    assert update["$inc"] == {"version": 1}


async def test_archive_retry_is_idempotent(archive_setup, monkeypatch):
    session, repo, service = archive_setup
    session.status = SessionStatus.ARCHIVED
    response = MagicMock()
    monkeypatch.setattr("services.session_service.SessionResponse.from_document", response)
    result = await service.archive_session(
        session.id, CurrentUser(user_id="owner", role="student"), BackgroundTasks()
    )
    assert result is response.return_value
    repo.archive.assert_not_awaited()
