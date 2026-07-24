"""
services/session_service.py

Business logic for the AGIS session lifecycle.

Session creation:
    1. Validate idempotency
    2. Validate active-session constraint
    3. Store complete founder PreEval input
    4. Create MongoDB session
    5. Move CREATED -> QUEUED
    6. Start TIPSC asynchronously
    7. Return immediately

TIPSC execution is direct/in-process.
DFV and Discovery remain flow-service controlled.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from datetime import datetime, timezone
from typing import Optional

from fastapi import BackgroundTasks

from exceptions.base import (
    ActiveSessionExistsError,
    CannotArchiveActiveSessionError,
    SessionNotFoundError,
)

from models.audit import AuditEvent
from repositories.session_repo import session_repo
from schemas.auth import CurrentUser
from schemas.session import (
    SessionListResponse,
    SessionResponse,
)
from services.audit_service import audit_service
from state_machine.states import (
    RUNNING_STATES,
    SessionStatus,
)


logger = logging.getLogger(__name__)


class SessionService:
    """
    Orchestrates the complete session lifecycle.
    """

    # ──────────────────────────────────────────────────────────────────────
    # CREATE SESSION
    # ──────────────────────────────────────────────────────────────────────

    async def create_session(
        self,
        student_id: str,
        team_id: str,
        problem_statement: str,
        customer_segment: str,
        consequence: str,
        assumptions: list[str],
        proposed_solution: str,
        target_geography: str,
        industry_sector: str,
        idempotency_key: str,
        background_tasks: BackgroundTasks,
    ) -> SessionResponse:

        # ── 1. Idempotency ────────────────────────────────────────────────

        existing = (
            await session_repo.find_by_idempotency_key(
                idempotency_key
            )
        )

        if existing:

            logger.info(
                "Idempotency hit | key=%s | session_id=%s",
                idempotency_key,
                existing.id,
            )

            return SessionResponse.from_document(
                existing
            )

        # ── 2. Active session guard ───────────────────────────────────────

        active = await session_repo.find_active_by_student(
            student_id
        )

        if active:

            logger.info(
                "Active session exists | "
                "student_id=%s | session_id=%s | status=%s",
                student_id,
                active.id,
                active.status,
            )

            raise ActiveSessionExistsError()

        # ── 3. Build founder PreEval input ────────────────────────────────

        preeval_input = {
            "problem_statement": problem_statement,
            "customer_segment": customer_segment,
            "consequence": consequence,
            "assumptions": assumptions,
            "proposed_solution": proposed_solution,
            "target_geography": target_geography,
            "industry_sector": industry_sector,
        }

        # ── 4. Create session ─────────────────────────────────────────────

        now = datetime.now(timezone.utc)

        session = await session_repo.create(
            {
                "student_id": student_id,
                "team_id": team_id,

                # Compatibility fields used by DFV / Discovery
                "problem_statement": problem_statement,
                "idea": proposed_solution,

                # Complete founder intake
                "preeval_input": preeval_input,

                "status": SessionStatus.CREATED,

                "version": 0,

                "idempotency_key": idempotency_key,

                "created_at": now,
                "updated_at": now,
            }
        )

        session_id = str(session.id)

        logger.info(
            "Session created | "
            "session_id=%s | student_id=%s",
            session_id,
            student_id,
        )

        # ── 5. Audit creation ─────────────────────────────────────────────

        background_tasks.add_task(
            audit_service.log_event,
            event=AuditEvent.SESSION_CREATED,
            actor=student_id,
            actor_role="student",
            session_id=session_id,
            metadata={
                "team_id": team_id,
                "idempotency_key": idempotency_key,
            },
        )

        # ── 6. CREATED -> QUEUED ─────────────────────────────────────────

        updated = await session_repo.update_status(
            session_id=session_id,
            new_status=SessionStatus.QUEUED,
            expected_version=session.version,
            current_status=SessionStatus.CREATED.value,
            actor="system",
            trigger="tipsc_queued",
        )

        if not updated:

            logger.error(
                "Failed to queue TIPSC session | "
                "session_id=%s",
                session_id,
            )

            raise RuntimeError(
                "Could not move session to queued state."
            )

        # ── 7. Correlation ID ─────────────────────────────────────────────

        correlation_id = str(uuid.uuid4())

        await session_repo.set_correlation_id(
            session_id=session_id,
            correlation_id=correlation_id,
        )

        # ── 8. Load TIPSC executor ────────────────────────────────────────

        from events import startup

        executor = startup.tipsc_executor_instance

        if executor is None:

            logger.error(
                "TIPSC executor unavailable | "
                "session_id=%s",
                session_id,
            )

            await session_repo.update_pipeline_state(
                session_id,
                {
                    "status": SessionStatus.TIPSC_FAILED.value,
                    "error": "TIPSC executor is not initialized.",
                },
            )

            raise RuntimeError(
                "TIPSC executor is not initialized."
            )

        # ── 9. Start TIPSC asynchronously ─────────────────────────────────

        task = asyncio.create_task(
            executor.run(
                session_id=session_id,
                preeval_input=preeval_input.copy(),
            )
        )

        # Keep task exception observable in logs.
        task.add_done_callback(
            lambda completed_task: (
                logger.error(
                    "TIPSC background task crashed | "
                    "session_id=%s | error=%s",
                    session_id,
                    completed_task.exception(),
                )
                if (
                    not completed_task.cancelled()
                    and completed_task.exception()
                    is not None
                )
                else None
            )
        )

        logger.info(
            "TIPSC task started | "
            "session_id=%s | correlation_id=%s",
            session_id,
            correlation_id,
        )

        # ── 10. Audit TIPSC trigger ───────────────────────────────────────

        background_tasks.add_task(
            audit_service.log_event,
            event=AuditEvent.TIPSC_TRIGGERED,
            actor=student_id,
            actor_role="student",
            session_id=session_id,
            metadata={
                "correlation_id": correlation_id,
                "execution": "direct_async_task",
            },
        )

        # ── 11. Return current MongoDB state ──────────────────────────────

        session = await session_repo.find_by_id(
            session_id
        )

        if session is None:

            raise SessionNotFoundError()

        return SessionResponse.from_document(
            session
        )

    # ──────────────────────────────────────────────────────────────────────
    # GET SESSION
    # ──────────────────────────────────────────────────────────────────────

    async def get_session(
        self,
        session_id: str,
        current_user: CurrentUser,
    ) -> SessionResponse:

        session = None

        if current_user.is_student:

            session = (
                await session_repo.find_by_id_and_student(
                    session_id=session_id,
                    student_id=current_user.user_id,
                )
            )

            if session is None and current_user.team_id:
                raw = await session_repo.find_by_id(session_id)
                if raw and raw.team_id == current_user.team_id:
                    session = raw

        elif current_user.is_mentor:

            raw = await session_repo.find_by_id(
                session_id
            )

            if (
                raw is not None
                and raw.team_id
                in (
                    current_user.mentor_team_ids
                    or []
                )
            ):

                session = raw

        else:

            session = await session_repo.find_by_id(
                session_id
            )

        if session is None:

            raise SessionNotFoundError()

        return SessionResponse.from_document(
            session
        )

    # ──────────────────────────────────────────────────────────────────────
    # LIST SESSIONS
    # ──────────────────────────────────────────────────────────────────────

    async def list_sessions(
        self,
        current_user: CurrentUser,
        filters: Optional[dict] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[
        list[SessionListResponse],
        int,
    ]:

        filters = filters or {}

        if current_user.is_student:

            sessions = await session_repo.find_by_student(
                student_id=current_user.user_id,
                filters=filters,
                page=page,
                limit=limit,
            )

            total = len(sessions)

            if len(sessions) == limit:
                total = page * limit + 1

        elif current_user.is_mentor:

            team_ids = (
                current_user.mentor_team_ids
                or []
            )

            sessions = await session_repo.find_by_teams(
                team_ids=team_ids,
                filters=filters,
                page=page,
                limit=limit,
            )

            total = len(sessions)

            if len(sessions) == limit:
                total = page * limit + 1

        else:

            sessions = (
                await session_repo.find_all_admin(
                    filters=filters,
                    page=page,
                    limit=limit,
                )
            )

            total = len(sessions)

            if len(sessions) == limit:
                total = page * limit + 1

        items = [
            SessionListResponse.from_document(
                session
            )
            for session in sessions
        ]

        return items, total

    # ──────────────────────────────────────────────────────────────────────
    # ARCHIVE SESSION
    # ──────────────────────────────────────────────────────────────────────

    async def archive_session(
        self,
        session_id: str,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
    ) -> SessionResponse:

        # Ownership validation
        await self.get_session(
            session_id=session_id,
            current_user=current_user,
        )

        session = await session_repo.find_by_id(
            session_id
        )

        if session is None:

            raise SessionNotFoundError()

        if session.status in RUNNING_STATES:

            raise CannotArchiveActiveSessionError(
                "Cannot archive session while it is "
                f"in state '{session.status.value}'."
            )

        previous_status = session.status.value

        archived = await session_repo.archive(
            session_id
        )

        if not archived:

            raise SessionNotFoundError()

        logger.info(
            "Session archived | "
            "session_id=%s | actor=%s",
            session_id,
            current_user.user_id,
        )

        background_tasks.add_task(
            audit_service.log_event,
            event=AuditEvent.SESSION_ARCHIVED,
            actor=current_user.user_id,
            actor_role=current_user.role,
            session_id=session_id,
            metadata={
                "previous_status": previous_status,
            },
        )

        updated = await session_repo.find_by_id(
            session_id
        )

        if updated is None:

            raise SessionNotFoundError()

        return SessionResponse.from_document(
            updated
        )


session_service = SessionService()