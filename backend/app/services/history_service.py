"""
services/history_service.py — Business logic for session history.

Responsibilities:
  - Enforce RBAC for history access
  - Retrieve audit logs for a session
  - Return paginated chronological history
"""

from __future__ import annotations

import logging

from app.exceptions.session import SessionNotFoundError
from app.models.audit import AuditLog
from app.repositories.audit_repo import audit_repo
from app.repositories.session_repo import session_repo
from app.repositories.user_repo import user_repo
from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)


class HistoryService:
    """Handles retrieval of session audit history."""

    async def get_session_history(
        self,
        session_id: str,
        current_user: CurrentUser,
        page: int = 1,
        limit: int = 20,
    ) -> list[AuditLog]:
        """
        Return chronological audit history for a session.

        Access Rules:
        - Student -> only own session
        - Mentor -> only sessions belonging to supervised teams
        - Admin -> any session

        Raises:
            SessionNotFoundError:
                - Session does not exist
                - User is not authorized to access the session
        """

        # Student
        if current_user.is_student:
            user = await user_repo.find_by_id(current_user.user_id)

            if user is None:
                raise SessionNotFoundError()

            session = await session_repo.find_by_id_and_student(
                session_id=session_id,
                student_id=current_user.user_id,
            )

            if session is None:
                raise SessionNotFoundError()

        # Mentor
        elif current_user.is_mentor:
            session = await session_repo.find_by_id(session_id)

            if (
                session is None
                or session.team_id not in (current_user.mentor_team_ids or [])
            ):
                raise SessionNotFoundError()

        # Admin
        elif current_user.is_admin:
            session = await session_repo.find_by_id(session_id)

            if session is None:
                raise SessionNotFoundError()

        # Unknown role
        else:
            raise SessionNotFoundError()

        logger.info(
            "History requested: session=%s user=%s role=%s",
            session_id,
            current_user.user_id,
            current_user.role,
        )

        history = await audit_repo.find_by_session(
            session_id=session_id,
            page=page,
            limit=limit,
        )

        return history


history_service = HistoryService()