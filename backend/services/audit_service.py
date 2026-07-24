"""
services/audit_service.py — Audit logging service.

Responsibilities:
  - Write immutable audit log entries to the `audit_logs` collection via AuditRepository.
  - Designed to run as a FastAPI BackgroundTask — does NOT block the HTTP response.
  - If the write fails, the error is logged to the application log and silently swallowed.
    The main operation is NEVER failed or rolled back due to an audit failure.

Usage from a route handler:
    background_tasks.add_task(
        audit_service.log_event,
        session_id=str(session.id),
        event=AuditEvent.SESSION_CREATED,
        actor=current_user.user_id,
        actor_role=current_user.role,
        metadata={"problem_statement": session.problem_statement},
    )

Design constraints:
  - Every audit entry is immutable once written (AuditRepository has no update/delete).
  - session_id is optional — auth events (login, logout) do not belong to a session.
  - actor may be a user_id, "system", or a worker identifier like "worker_tipsc".
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from models.audit import AuditEvent
from repositories.audit_repo import audit_repo

logger = logging.getLogger(__name__)


class AuditService:
    """
    Thin service layer over AuditRepository.

    Exists to:
      1. Provide a consistent call signature that route handlers pass to BackgroundTask.
      2. Swallow write errors so a failing audit never breaks the main operation.
    """

    async def log_event(
        self,
        event: AuditEvent | str,
        actor: str,
        actor_role: str,
        metadata: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Write an immutable audit log entry.

        This method is designed to be scheduled via FastAPI BackgroundTask:
            background_tasks.add_task(
                audit_service.log_event,
                event=AuditEvent.SESSION_CREATED,
                actor=user.user_id,
                actor_role=user.role,
                session_id=str(session.id),
                metadata={...},
            )

        Failure policy:
            - If the database write fails for any reason, the exception is caught,
              logged at ERROR level, and the method returns normally.
            - The caller (route handler or service) is never informed of audit failures.
            - This ensures audit never becomes a single point of failure.

        Args:
            event       : AuditEvent enum value or raw string (e.g. "SESSION_CREATED").
            actor       : user_id string, "system", or worker identifier.
            actor_role  : One of "student" | "mentor" | "admin" | "worker" | "system".
            metadata    : Arbitrary dict for structured context (IDs, names, etc.).
            session_id  : Linked session's string ID. None for auth/system events.
        """
        try:
            await audit_repo.create_event(
                event=event,
                actor=actor,
                actor_role=actor_role,
                metadata=metadata or {},
                session_id=session_id,
            )
            logger.debug(
                "Audit log written | event=%s | actor=%s | session_id=%s",
                event,
                actor,
                session_id,
            )
        except Exception as exc:  # noqa: BLE001
            # Never propagate — audit write failure must not affect the main request.
            logger.error(
                "Audit log write failed (non-fatal) | event=%s | actor=%s | session_id=%s | error=%s",
                event,
                actor,
                session_id,
                exc,
                exc_info=True,
            )


# Module-level singleton — stateless, safe to share across requests.
audit_service = AuditService()
