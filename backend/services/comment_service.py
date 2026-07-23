"""
Comment service — mentor comments on sessions.

Depends on three collaborators, injected via the constructor (same pattern
as flow_service.py on B-12), so this can be unit tested with no real
MongoDB:

- comment_repo: create(), find_by_session(), find_by_id(),
                find_by_id_and_mentor(), soft_delete()
                -> repositories/comment_repo.py, Bhavesh (B-11)
- session_repo: find_by_id() — just enough to check the session exists and
                read student_id/team_id for the permission checks below
                -> repositories/session_repo.py, Bhavesh (B-04)
- audit_service: log_event(session_id, event, actor, actor_role, metadata)
                -> services/audit_service.py, Palash (B-08)

Spec conflict worth resolving before merge: api-spec.md Section 6.1 and
the Day 3 acceptance criteria both say a mentor commenting on an
unassigned team's session returns 403 INSUFFICIENT_PERMISSIONS. But
rbac.md's edge case table (R11) says this should be 404 SESSION_NOT_FOUND,
matching the "resource filter hides it before the check runs" pattern used
everywhere else a mentor touches an unsupervised session. I've gone with
403 here since that's what's explicitly graded on Day 3 — flip the raise
in `_check_can_comment` to `SessionNotFoundError` if the team decides R11
is the correct behavior instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from exceptions.base import (
    CommentNotFoundError,
    InsufficientPermissionsError,
    SessionNotFoundError,
)


@dataclass
class SessionAccessInfo:
    """Minimal session shape this service needs for permission checks."""

    session_id: str
    student_id: str
    team_id: str


@dataclass
class Comment:
    comment_id: str
    session_id: str
    mentor_id: str
    mentor_name: str
    comment: str
    created_at: datetime
    deleted: bool = False


class CurrentUserLike(Protocol):
    """Structural type matching dependencies.auth.CurrentUser — not
    imported directly so this module has no dependency on Palash's branch."""

    user_id: str
    role: str
    team_id: Optional[str]
    mentor_team_ids: list[str]


class SessionRepoProtocol(Protocol):
    async def find_by_id(self, session_id: str) -> Optional[SessionAccessInfo]: ...


class CommentRepoProtocol(Protocol):
    async def create(
        self, session_id: str, mentor_id: str, mentor_name: str, comment: str
    ) -> Comment: ...

    async def find_by_session(self, session_id: str) -> list[Comment]: ...

    async def find_by_id(self, comment_id: str) -> Optional[Comment]: ...

    async def find_by_id_and_mentor(
        self, comment_id: str, mentor_id: str
    ) -> Optional[Comment]: ...

    async def soft_delete(self, comment_id: str) -> bool: ...


class AuditServiceProtocol(Protocol):
    async def log_event(
        self,
        session_id: str,
        event: str,
        actor: str,
        actor_role: str,
        metadata: dict[str, Any],
    ) -> None: ...


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class CommentService:
    def __init__(
        self,
        comment_repo: CommentRepoProtocol,
        session_repo: SessionRepoProtocol,
        audit_service: AuditServiceProtocol,
    ) -> None:
        self._comments = comment_repo
        self._sessions = session_repo
        self._audit = audit_service

    async def _load_session_or_404(self, session_id: str) -> SessionAccessInfo:
        session = await self._sessions.find_by_id(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    def _check_can_view(
        self, session: SessionAccessInfo, current_user: CurrentUserLike
    ) -> None:
        if current_user.role == "admin":
            return
        if current_user.role == "student":
            if session.student_id != current_user.user_id:
                # Ownership-filtered: "not yours" looks identical to "doesn't
                # exist" to the caller.
                raise SessionNotFoundError(f"No session found with id '{session.session_id}'")
            return
        if current_user.role == "mentor":
            if session.team_id not in current_user.mentor_team_ids:
                raise SessionNotFoundError(f"No session found with id '{session.session_id}'")
            return
        raise InsufficientPermissionsError()

    def _check_can_comment(
        self, session: SessionAccessInfo, current_user: CurrentUserLike
    ) -> None:
        if current_user.role == "admin":
            return
        if current_user.role != "mentor":
            raise InsufficientPermissionsError("Only mentors and admins can comment")
        if session.team_id not in current_user.mentor_team_ids:
            # See module docstring re: 403 vs 404 (rbac.md R11) conflict.
            raise InsufficientPermissionsError(
                "You are not assigned to this session's team"
            )

    # -- public API ----------------------------------------------------------

    async def add_comment(
        self, session_id: str, current_user: CurrentUserLike, comment_text: str
    ) -> Comment:
        session = await self._load_session_or_404(session_id)
        self._check_can_comment(session, current_user)

        comment = await self._comments.create(
            session_id=session_id,
            mentor_id=current_user.user_id,
            mentor_name=getattr(current_user, "name", current_user.user_id),
            comment=comment_text,
        )

        await self._audit.log_event(
            session_id,
            "COMMENT_ADDED",
            current_user.user_id,
            current_user.role,
            {"comment_id": comment.comment_id},
        )

        return comment

    async def get_comments(
        self, session_id: str, current_user: CurrentUserLike
    ) -> list[Comment]:
        session = await self._load_session_or_404(session_id)
        self._check_can_view(session, current_user)
        return await self._comments.find_by_session(session_id)

    async def delete_comment(
        self, comment_id: str, current_user: CurrentUserLike
    ) -> None:
        if current_user.role == "admin":
            comment = await self._comments.find_by_id(comment_id)
            if comment is None:
                raise CommentNotFoundError(comment_id)
        elif current_user.role == "mentor":
            comment = await self._comments.find_by_id_and_mentor(
                comment_id, current_user.user_id
            )
            if comment is None:
                # Distinguish "doesn't exist" from "exists but isn't yours"
                # so we return the right error code (404 vs 403), unlike
                # the session ownership checks above which deliberately
                # collapse those two cases.
                exists = await self._comments.find_by_id(comment_id)
                if exists is None:
                    raise CommentNotFoundError(comment_id)
                raise InsufficientPermissionsError(
                    "You can only delete your own comments"
                )
        else:
            raise InsufficientPermissionsError(
                "Only the comment author or an admin can delete comments"
            )

        deleted = await self._comments.soft_delete(comment_id)
        if not deleted:
            raise CommentNotFoundError(comment_id)

        await self._audit.log_event(
            comment.session_id,
            "COMMENT_DELETED",
            current_user.user_id,
            current_user.role,
            {"comment_id": comment_id},
        )
