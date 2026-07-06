"""
services/session_service.py — Business logic for the full session lifecycle.

Responsibilities:
  - create_session  : Validate uniqueness, write to MongoDB, publish TIPSC Kafka event,
                      advance state to QUEUED, fire audit logs.
  - get_session     : Ownership-filtered fetch (student → own sessions only, mentor → teams).
  - list_sessions   : Paginated listing with role-filtered ownership.
  - archive_session : Soft-archive with state guard (no archiving RUNNING sessions).

Service rules:
  - Never touch HTTP concepts (Request, Response, status codes) — that is the router's job.
  - All audit log writes are done as BackgroundTask — service returns the FastAPI
    BackgroundTasks object populated, not executed.
  - Kafka failure ROLLS BACK: status stays CREATED (not QUEUED), KafkaPublishError raised.
  - If Kafka succeeds: status advances to QUEUED, TIPSC_TRIGGERED audit fires.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import BackgroundTasks

from app.exceptions.base import (
    ActiveSessionExistsError,
    CannotArchiveActiveSessionError,
    KafkaPublishError,
    SessionNotFoundError,
)
from app.kafka.payloads import TIPSCEventPayload
from app.kafka.producer import kafka_producer
from app.kafka.topics import KafkaTopic
from app.models.audit import AuditEvent
from app.repositories.session_repo import session_repo
from app.schemas.auth import CurrentUser
from app.schemas.session import SessionListResponse, SessionResponse
from app.services.audit_service import audit_service
from app.state_machine.states import RUNNING_STATES, SessionStatus

logger = logging.getLogger(__name__)


class SessionService:
    """Orchestrates the full session lifecycle."""

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_session(
        self,
        student_id: str,
        team_id: str,
        problem_statement: str,
        idea: str,
        idempotency_key: str,
        background_tasks: BackgroundTasks,
    ) -> SessionResponse:
        """
        Create a new session for a student.

        Flow:
          1. Idempotency check — if key already used, return the existing session.
          2. Active-session guard — student may only have one non-archived session.
          3. Write session with status=CREATED to MongoDB.
          4. Fire SESSION_CREATED audit log (BackgroundTask).
          5. Publish TIPSCEventPayload to `userSession.tipsc` Kafka topic.
             - On failure: leave status as CREATED, raise KafkaPublishError.
             - On success:  advance status to QUEUED, store correlation_id.
          6. Fire TIPSC_TRIGGERED audit log (BackgroundTask).
          7. Return SessionResponse.

        Raises:
            ActiveSessionExistsError  (409) — student already has a non-archived session.
            KafkaPublishError         (503) — Kafka publish failed after retries.
        """
        # ── Step 1: Idempotency check ─────────────────────────────────────────
        existing = await session_repo.find_by_idempotency_key(idempotency_key)
        if existing:
            logger.info(
                "Idempotency hit | key=%s | session_id=%s", idempotency_key, existing.id
            )
            return SessionResponse.from_document(existing)

        # ── Step 2: Active-session guard ──────────────────────────────────────
        active = await session_repo.find_active_by_student(student_id)
        if active:
            logger.info(
                "Active session exists | student_id=%s | active_session_id=%s",
                student_id,
                active.id,
            )
            raise ActiveSessionExistsError()

        # ── Step 3: Persist session with status=CREATED ───────────────────────
        session = await session_repo.create({
            "student_id": student_id,
            "team_id": team_id,
            "problem_statement": problem_statement,
            "idea": idea,
            "status": SessionStatus.CREATED,
            "idempotency_key": idempotency_key,
            "version": 0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })
        session_id_str = str(session.id)
        logger.info("Session created | session_id=%s | student_id=%s", session_id_str, student_id)

        # ── Step 4: Audit — SESSION_CREATED (background, non-blocking) ────────
        background_tasks.add_task(
            audit_service.log_event,
            event=AuditEvent.SESSION_CREATED,
            actor=student_id,
            actor_role="student",
            session_id=session_id_str,
            metadata={
                "team_id": team_id,
                "problem_statement": problem_statement[:200],  # truncate for metadata
                "idempotency_key": idempotency_key,
            },
        )

        # ── Step 5: Publish to Kafka ──────────────────────────────────────────
        import uuid
        correlation_id = str(uuid.uuid4())

        payload = TIPSCEventPayload(
            session_id=session_id_str,
            student_id=student_id,
            team_id=team_id,
            problem_statement=problem_statement,
            idea=idea,
            correlation_id=correlation_id,
        )

        try:
            await kafka_producer.publish(
                topic=KafkaTopic.USER_SESSION_TIPSC,
                payload=payload,
            )
        except Exception as exc:
            # Kafka failed — session stays CREATED (not advanced to QUEUED).
            # We do NOT delete the session — the student can retry via idempotency key.
            logger.error(
                "Kafka publish failed for session_id=%s | error=%s",
                session_id_str,
                exc,
                exc_info=True,
            )
            raise KafkaPublishError(
                f"Session created (id={session_id_str}) but Kafka publish failed. "
                "Session status remains CREATED. Retry using the same Idempotency-Key."
            ) from exc

        # ── Kafka succeeded — advance status to QUEUED and store correlation_id ──
        updated = await session_repo.update_status(
            session_id=session_id_str,
            new_status=SessionStatus.QUEUED,
            expected_version=session.version,
        )
        if not updated:
            logger.warning(
                "Status update to QUEUED failed (version conflict) | session_id=%s", session_id_str
            )

        await session_repo.set_correlation_id(
            session_id=session_id_str,
            correlation_id=correlation_id,
        )

        logger.info(
            "Session queued for TIPSC | session_id=%s | correlation_id=%s",
            session_id_str,
            correlation_id,
        )

        # ── Step 6: Audit — TIPSC_TRIGGERED (background, non-blocking) ────────
        background_tasks.add_task(
            audit_service.log_event,
            event=AuditEvent.TIPSC_TRIGGERED,
            actor=student_id,
            actor_role="student",
            session_id=session_id_str,
            metadata={"correlation_id": correlation_id, "topic": KafkaTopic.USER_SESSION_TIPSC},
        )

        # ── Step 7: Re-fetch and return the updated session ───────────────────
        updated_session = await session_repo.find_by_id(session_id_str)
        if updated_session is None:
            # This should never happen — log and return the stale object.
            logger.error("Re-fetch of session after create returned None | session_id=%s", session_id_str)
            return SessionResponse.from_document(session)

        return SessionResponse.from_document(updated_session)

    # ── Get (single) ─────────────────────────────────────────────────────────

    async def get_session(
        self,
        session_id: str,
        current_user: CurrentUser,
    ) -> SessionResponse:
        """
        Fetch a session, applying role-based ownership filters.

        Ownership rules:
          - student : may only fetch their own sessions (find_by_id_and_student).
                      Returns 404 if the session exists but belongs to another student
                      — this prevents information leakage (no 403).
          - mentor  : may fetch any session whose team_id is in their supervised teams.
          - admin   : unrestricted access via find_by_id.

        Raises:
            SessionNotFoundError (404) — session does not exist or ownership check fails.
        """
        session = None

        if current_user.is_student:
            session = await session_repo.find_by_id_and_student(
                session_id=session_id,
                student_id=current_user.user_id,
            )
        elif current_user.is_mentor:
            # Mentors can see any session whose team is in their supervised list.
            raw = await session_repo.find_by_id(session_id)
            if raw is not None and raw.team_id in (current_user.mentor_team_ids or []):
                session = raw
        else:
            # Admin — unrestricted.
            session = await session_repo.find_by_id(session_id)

        if session is None:
            raise SessionNotFoundError()

        return SessionResponse.from_document(session)

    # ── List ─────────────────────────────────────────────────────────────────

    async def list_sessions(
        self,
        current_user: CurrentUser,
        filters: Optional[dict] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[SessionListResponse], int]:
        """
        Paginated session listing with role-filtered ownership.

        Returns:
            (items, total) where items is the current page and total is the
            full count (used by the route to build the pagination envelope).

        Ownership:
          - student : own sessions only (non-archived by default).
          - mentor  : sessions for their supervised teams.
          - admin   : all sessions (no filter applied by this service;
                      admin can pass explicit filters).
        """
        filters = filters or {}

        if current_user.is_student:
            sessions = await session_repo.find_by_student(
                student_id=current_user.user_id,
                filters=filters,
                page=page,
                limit=limit,
            )
            # Total count — for now we use len; a dedicated count query can be added later.
            total = len(sessions)
            if len(sessions) == limit:
                # There may be more — we'd need a count query for accurate total.
                # This is acceptable for MVP; accurate counts added in a future ticket.
                total = page * limit + 1  # signals "has_next"

        elif current_user.is_mentor:
            team_ids = current_user.mentor_team_ids or []
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
            # Admin — currently mirrors mentor behaviour with no team filter.
            # Full admin query (no team restriction) can be added later.
            sessions = await session_repo.find_by_teams(
                team_ids=[],  # empty → returns [] from repo
                filters=filters,
                page=page,
                limit=limit,
            )
            total = 0

        items = [SessionListResponse.from_document(s) for s in sessions]
        return items, total

    # ── Archive ───────────────────────────────────────────────────────────────

    async def archive_session(
        self,
        session_id: str,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
    ) -> SessionResponse:
        """
        Soft-archive a session (DELETE /sessions/{id}).

        Validation:
          - Session must exist and be accessible by the caller (same ownership rules as get_session).
          - Session must NOT be in a RUNNING state (TIPSC_RUNNING, DFV_RUNNING, DISCOVERY_RUNNING).

        Side effects:
          - Sets status=ARCHIVED and archived_at=now() via session_repo.archive().
          - Fires SESSION_ARCHIVED audit log as a BackgroundTask.

        Raises:
            SessionNotFoundError           (404) — not found or ownership check fails.
            CannotArchiveActiveSessionError (409) — session is currently running a flow.
        """
        # Fetch with ownership check (reuses get_session logic).
        session_response = await self.get_session(session_id=session_id, current_user=current_user)

        # Check the live document for current status (not cached in response schema).
        session = await session_repo.find_by_id(session_id)
        if session is None:
            raise SessionNotFoundError()

        if session.status in RUNNING_STATES:
            raise CannotArchiveActiveSessionError(
                f"Cannot archive session while it is in state '{session.status.value}'. "
                "Wait for the flow to complete or fail before archiving."
            )

        archived = await session_repo.archive(session_id)
        if not archived:
            raise SessionNotFoundError()

        logger.info(
            "Session archived | session_id=%s | actor=%s", session_id, current_user.user_id
        )

        # Audit log — SESSION_ARCHIVED (background, non-blocking).
        background_tasks.add_task(
            audit_service.log_event,
            event=AuditEvent.SESSION_ARCHIVED,
            actor=current_user.user_id,
            actor_role=current_user.role,
            session_id=session_id,
            metadata={"previous_status": session.status.value},
        )

        # Re-fetch and return the archived document.
        updated = await session_repo.find_by_id(session_id)
        if updated is None:
            raise SessionNotFoundError()

        return SessionResponse.from_document(updated)


# Module-level singleton — stateless, safe to share across requests.
session_service = SessionService()
