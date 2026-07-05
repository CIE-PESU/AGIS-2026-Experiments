"""
services/comment_service.py — Business logic for mentor comments.

Responsibilities:
  - add_comment    : Mentor can comment on sessions their team owns.
  - get_comments   : RBAC-filtered retrieval (same rules as session access).
  - delete_comment : Mentor deletes own comment; admin deletes any.

Architecture rule: This service only coordinates between comment_repo,
session_repo, and audit_service. No HTTP concepts allowed here.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import BackgroundTasks

from app.exceptions.base import (
    CommentNotFoundError,
    InsufficientPermissionsError,
    SessionNotFoundError,
)
from app.models.audit import AuditEvent
from app.models.comment import MentorComment
from app.repositories.comment_repo import comment_repo
from app.repositories.session_repo import session_repo
from app.schemas.auth import CurrentUser
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)


class CommentService:
    """Orchestrates mentor comment lifecycle."""

    # ── Add Comment ──────────────────────────────────────────────────────────

    async def add_comment(
        self,
        session_id: str,
        comment_text: str,
        current_user: CurrentUser,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> MentorComment:
        """
        Add a mentor comment to a session.

        Authorization:
          - Only mentors and admins can add comments.
          - Mentors may only comment on sessions belonging to their supervised teams.
          - Admins may comment on any session.

        Raises:
            SessionNotFoundError     (404) — session does not exist.
            InsufficientPermissionsError (403) — mentor not assigned to this session's team.
        """
        # Fetch session (no ownership filter — we check team membership manually below)
        session = await session_repo.find_by_id(session_id)
        if session is None:
            raise SessionNotFoundError()

        # Mentors can only comment on their supervised teams
        if current_user.is_mentor:
            if session.team_id not in (current_user.mentor_team_ids or []):
                raise InsufficientPermissionsError(
                    "You are not assigned to this session's team and cannot comment on it."
                )

        # Admins bypass team restriction
        comment = await comment_repo.create(
            session_id=session_id,
            mentor_id=current_user.user_id,
            mentor_name=current_user.user_id,  # name comes from JWT display_name if added; fall back to user_id
            comment=comment_text,
        )

        logger.info(
            "Comment added | session_id=%s | mentor_id=%s | comment_id=%s",
            session_id,
            current_user.user_id,
            str(comment.id),
        )

        # Audit log — non-blocking
        if background_tasks is not None:
            background_tasks.add_task(
                audit_service.log_event,
                event=AuditEvent.COMMENT_ADDED,
                actor=current_user.user_id,
                actor_role=current_user.role,
                session_id=session_id,
                metadata={"comment_id": str(comment.id)},
            )
        else:
            await audit_service.log_event(
                event=AuditEvent.COMMENT_ADDED,
                actor=current_user.user_id,
                actor_role=current_user.role,
                session_id=session_id,
                metadata={"comment_id": str(comment.id)},
            )

        return comment

    # ── Get Comments ─────────────────────────────────────────────────────────

    async def get_comments(
        self,
        session_id: str,
        current_user: CurrentUser,
    ) -> list[MentorComment]:
        """
        Retrieve all non-deleted comments for a session.

        Access rules (mirror session access rules):
          - student : only own sessions (404 if belongs to another student)
          - mentor  : sessions in supervised teams
          - admin   : any session

        Raises:
            SessionNotFoundError (404)
        """
        session = await session_repo.find_by_id(session_id)
        if session is None:
            raise SessionNotFoundError()

        if current_user.is_student:
            if session.student_id != current_user.user_id:
                raise SessionNotFoundError()  # 404, not 403 — prevents info leak

        elif current_user.is_mentor:
            if session.team_id not in (current_user.mentor_team_ids or []):
                raise SessionNotFoundError()

        # Admin: no additional check needed

        return await comment_repo.find_by_session(session_id)

    # ── Delete Comment ────────────────────────────────────────────────────────

    async def delete_comment(
        self,
        comment_id: str,
        current_user: CurrentUser,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> None:
        """
        Soft-delete a comment.

        Authorization:
          - Mentor: can only delete their OWN comments.
          - Admin: can delete any comment.

        Raises:
            CommentNotFoundError     (404) — comment not found.
            InsufficientPermissionsError (403) — mentor trying to delete another mentor's comment.
        """
        comment = await comment_repo.find_by_id(comment_id)
        if comment is None:
            raise CommentNotFoundError()

        if current_user.is_mentor:
            # Ownership check: mentor can only delete their own comments
            if comment.mentor_id != current_user.user_id:
                raise InsufficientPermissionsError(
                    "You can only delete your own comments."
                )

        deleted = await comment_repo.soft_delete(comment_id)
        if not deleted:
            raise CommentNotFoundError()

        logger.info(
            "Comment soft-deleted | comment_id=%s | actor=%s",
            comment_id,
            current_user.user_id,
        )

        # Audit log — non-blocking
        if background_tasks is not None:
            background_tasks.add_task(
                audit_service.log_event,
                event=AuditEvent.COMMENT_DELETED,
                actor=current_user.user_id,
                actor_role=current_user.role,
                session_id=comment.session_id,
                metadata={"comment_id": comment_id},
            )
        else:
            await audit_service.log_event(
                event=AuditEvent.COMMENT_DELETED,
                actor=current_user.user_id,
                actor_role=current_user.role,
                session_id=comment.session_id,
                metadata={"comment_id": comment_id},
            )


# Module-level singleton — stateless, safe to share across requests.
comment_service = CommentService()
