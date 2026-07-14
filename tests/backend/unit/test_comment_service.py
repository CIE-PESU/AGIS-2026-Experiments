"""
Unit tests for CommentService (B-17). Uses fake in-memory repos/audit so
these run without a real MongoDB and without Bhavesh's/Palash's branches
being merged yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from services.comment_exceptions import (
    CommentNotFoundError,
    InsufficientPermissionsError,
    SessionNotFoundError,
)
from services.comment_service import (
    Comment,
    CommentService,
    SessionAccessInfo,
)


@dataclass
class FakeUser:
    user_id: str
    role: str
    team_id: str | None = None
    mentor_team_ids: list[str] = field(default_factory=list)
    name: str = "Test User"


class FakeSessionRepo:
    def __init__(self, sessions: dict[str, SessionAccessInfo]):
        self.sessions = sessions

    async def find_by_id(self, session_id):
        return self.sessions.get(session_id)


class FakeCommentRepo:
    def __init__(self):
        self._comments: dict[str, Comment] = {}
        self._counter = 0

    async def create(self, session_id, mentor_id, mentor_name, comment):
        self._counter += 1
        c = Comment(
            comment_id=f"cmt_{self._counter}",
            session_id=session_id,
            mentor_id=mentor_id,
            mentor_name=mentor_name,
            comment=comment,
            created_at="2026-07-06T00:00:00Z",
        )
        self._comments[c.comment_id] = c
        return c

    async def find_by_session(self, session_id):
        return [
            c
            for c in self._comments.values()
            if c.session_id == session_id and not c.deleted
        ]

    async def find_by_id(self, comment_id):
        c = self._comments.get(comment_id)
        if c is None or c.deleted:
            return None
        return c

    async def find_by_id_and_mentor(self, comment_id, mentor_id):
        c = self._comments.get(comment_id)
        if c is None or c.deleted or c.mentor_id != mentor_id:
            return None
        return c

    async def soft_delete(self, comment_id):
        c = self._comments.get(comment_id)
        if c is None:
            return False
        c.deleted = True
        return True


class FakeAuditService:
    def __init__(self):
        self.events = []

    async def log_event(self, session_id, event, actor, actor_role, metadata):
        self.events.append((session_id, event, actor, actor_role, metadata))


def build_service(sessions: dict[str, SessionAccessInfo]):
    session_repo = FakeSessionRepo(sessions)
    comment_repo = FakeCommentRepo()
    audit = FakeAuditService()
    return CommentService(comment_repo, session_repo, audit), comment_repo, audit


SESSION = SessionAccessInfo(session_id="ses_1", student_id="stu_1", team_id="team_1")


# ---------------------------------------------------------------------------
# add_comment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_cannot_add_comment():
    service, *_ = build_service({SESSION.session_id: SESSION})
    student = FakeUser(user_id="stu_1", role="student")

    with pytest.raises(InsufficientPermissionsError):
        await service.add_comment(SESSION.session_id, student, "a" * 20)


@pytest.mark.asyncio
async def test_mentor_on_unassigned_team_cannot_add_comment():
    service, *_ = build_service({SESSION.session_id: SESSION})
    mentor = FakeUser(user_id="mentor_1", role="mentor", mentor_team_ids=["team_2"])

    with pytest.raises(InsufficientPermissionsError):
        await service.add_comment(SESSION.session_id, mentor, "a" * 20)


@pytest.mark.asyncio
async def test_mentor_on_assigned_team_can_add_comment():
    service, comment_repo, audit = build_service({SESSION.session_id: SESSION})
    mentor = FakeUser(user_id="mentor_1", role="mentor", mentor_team_ids=["team_1"])

    comment = await service.add_comment(SESSION.session_id, mentor, "a" * 20)

    assert comment.mentor_id == "mentor_1"
    assert audit.events[-1][1] == "COMMENT_ADDED"


@pytest.mark.asyncio
async def test_admin_can_add_comment_to_any_session():
    service, comment_repo, audit = build_service({SESSION.session_id: SESSION})
    admin = FakeUser(user_id="admin_1", role="admin")

    comment = await service.add_comment(SESSION.session_id, admin, "a" * 20)

    assert comment.mentor_id == "admin_1"


@pytest.mark.asyncio
async def test_add_comment_session_not_found():
    service, *_ = build_service({})
    mentor = FakeUser(user_id="mentor_1", role="mentor", mentor_team_ids=["team_1"])

    with pytest.raises(SessionNotFoundError):
        await service.add_comment("ses_missing", mentor, "a" * 20)


# ---------------------------------------------------------------------------
# get_comments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_student_can_view_own_session_comments():
    service, comment_repo, _ = build_service({SESSION.session_id: SESSION})
    mentor = FakeUser(user_id="mentor_1", role="mentor", mentor_team_ids=["team_1"])
    await service.add_comment(SESSION.session_id, mentor, "a" * 20)

    student = FakeUser(user_id="stu_1", role="student")
    comments = await service.get_comments(SESSION.session_id, student)

    assert len(comments) == 1


@pytest.mark.asyncio
async def test_student_cannot_view_other_students_session_comments():
    service, *_ = build_service({SESSION.session_id: SESSION})
    other_student = FakeUser(user_id="stu_2", role="student")

    with pytest.raises(SessionNotFoundError):
        await service.get_comments(SESSION.session_id, other_student)


@pytest.mark.asyncio
async def test_mentor_cannot_view_unassigned_team_session_comments():
    service, *_ = build_service({SESSION.session_id: SESSION})
    mentor = FakeUser(user_id="mentor_2", role="mentor", mentor_team_ids=["team_9"])

    with pytest.raises(SessionNotFoundError):
        await service.get_comments(SESSION.session_id, mentor)


# ---------------------------------------------------------------------------
# delete_comment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mentor_can_delete_own_comment():
    service, comment_repo, audit = build_service({SESSION.session_id: SESSION})
    mentor = FakeUser(user_id="mentor_1", role="mentor", mentor_team_ids=["team_1"])
    comment = await service.add_comment(SESSION.session_id, mentor, "a" * 20)

    await service.delete_comment(comment.comment_id, mentor)

    remaining = await service.get_comments(
        SESSION.session_id, FakeUser(user_id="admin_1", role="admin")
    )
    assert remaining == []
    assert audit.events[-1][1] == "COMMENT_DELETED"


@pytest.mark.asyncio
async def test_mentor_cannot_delete_another_mentors_comment():
    service, *_ = build_service({SESSION.session_id: SESSION})
    mentor_a = FakeUser(user_id="mentor_a", role="mentor", mentor_team_ids=["team_1"])
    mentor_b = FakeUser(user_id="mentor_b", role="mentor", mentor_team_ids=["team_1"])
    comment = await service.add_comment(SESSION.session_id, mentor_a, "a" * 20)

    with pytest.raises(InsufficientPermissionsError):
        await service.delete_comment(comment.comment_id, mentor_b)


@pytest.mark.asyncio
async def test_admin_can_delete_any_comment():
    service, *_ = build_service({SESSION.session_id: SESSION})
    mentor = FakeUser(user_id="mentor_1", role="mentor", mentor_team_ids=["team_1"])
    admin = FakeUser(user_id="admin_1", role="admin")
    comment = await service.add_comment(SESSION.session_id, mentor, "a" * 20)

    await service.delete_comment(comment.comment_id, admin)  # should not raise


@pytest.mark.asyncio
async def test_delete_nonexistent_comment_raises_not_found():
    service, *_ = build_service({SESSION.session_id: SESSION})
    admin = FakeUser(user_id="admin_1", role="admin")

    with pytest.raises(CommentNotFoundError):
        await service.delete_comment("cmt_missing", admin)


@pytest.mark.asyncio
async def test_soft_deleted_comment_excluded_from_get_comments():
    service, comment_repo, _ = build_service({SESSION.session_id: SESSION})
    mentor = FakeUser(user_id="mentor_1", role="mentor", mentor_team_ids=["team_1"])
    c1 = await service.add_comment(SESSION.session_id, mentor, "first comment here")
    c2 = await service.add_comment(SESSION.session_id, mentor, "second comment here")

    await service.delete_comment(c1.comment_id, mentor)

    student = FakeUser(user_id="stu_1", role="student")
    comments = await service.get_comments(SESSION.session_id, student)

    assert [c.comment_id for c in comments] == [c2.comment_id]