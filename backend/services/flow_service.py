"""
services/flow_service.py

Flow orchestration service.

TIPSC:
    Runs directly through AsyncPipelineExecutor.

DFV / Discovery:
    Remain Kafka-driven.

Follow-up:
    Founder answer resumes the parked TIPSC pipeline.
"""

from __future__ import annotations

import asyncio
import uuid

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from models.schema import (
    DFVJobMessage,
    DFVJobPayload,
    DiscoveryJobMessage,
    DiscoveryJobPayload,
)
from kafka.topics import KafkaTopic

from services.flow_exceptions import (
    DFVNotUnlockedError,
    InvalidStateTransitionError,
    KafkaUnavailableError,
    SessionNotFoundError,
    SessionUpdateConflictError,
)

from state_machine.exceptions import (
    InvalidStateTransitionError as StateMachineInvalidTransitionError,
)

from state_machine.states import SessionStatus
from state_machine.validator import validate_transition


DFV_TOPIC = KafkaTopic.USER_SESSION_DFV
DISCOVERY_TOPIC = KafkaTopic.USER_SESSION_DISCOVERY


# ─────────────────────────────────────────────────────────────────────────────
# Session snapshot
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class SessionSnapshot:

    session_id: str

    student_id: str

    team_id: str

    status: SessionStatus

    version: int

    problem_statement: str

    idea: str

    preeval_input: Optional[dict[str, Any]] = None

    tipsc: Optional[dict[str, Any]] = None

    dfv: Optional[dict[str, Any]] = None

    pending_question: Optional[str] = None

    pending_answer: Optional[str] = None

    followup_turn: int = 0

    followup_history: Optional[list[dict[str, Any]]] = None

    correlation_id: Optional[str] = None

    @property
    def id(self) -> str:
        return self.session_id


# ─────────────────────────────────────────────────────────────────────────────
# Repository contract
# ─────────────────────────────────────────────────────────────────────────────


class SessionRepoProtocol(Protocol):

    async def find_by_id_and_student(
        self,
        session_id: str,
        student_id: str,
    ) -> Optional[SessionSnapshot]:
        ...

    async def update_status(
        self,
        session_id: str,
        new_status: SessionStatus,
        expected_version: int,
    ) -> bool:
        ...

    async def set_correlation_id(
        self,
        session_id: str,
        correlation_id: str,
    ) -> None:
        ...

    async def update_dfv_inputs(
        self,
        session_id: str,
        dfv_inputs: dict,
    ) -> bool:
        ...


class KafkaProducerProtocol(Protocol):

    async def publish(
        self,
        topic: str,
        payload: dict[str, Any],
    ) -> str:
        ...


class AuditServiceProtocol(Protocol):

    async def log_event(
        self,
        session_id: str,
        event: str,
        actor: str,
        actor_role: str,
        metadata: dict[str, Any],
    ) -> None:
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _now_iso() -> str:

    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _new_correlation_id() -> str:

    return f"cor_{uuid.uuid4().hex}"


def _base_kafka_payload(
    session: SessionSnapshot,
    flow: str,
    correlation_id: str,
) -> dict[str, Any]:

    return {
        "event_id": str(uuid.uuid4()),
        "correlation_id": correlation_id,
        "session_id": str(session.id),
        "team_id": session.team_id,
        "student_id": session.student_id,
        "flow": flow,
        "timestamp": _now_iso(),
        "schema_version": "1.0",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Flow service
# ─────────────────────────────────────────────────────────────────────────────


class FlowService:

    def __init__(
        self,
        session_repo: SessionRepoProtocol,
        kafka_producer: KafkaProducerProtocol,
        audit_service: AuditServiceProtocol,
    ) -> None:

        self._session_repo = session_repo

        self._kafka = kafka_producer

        self._audit = audit_service


    # ──────────────────────────────────────────────────────────────────────
    # Shared helpers
    # ──────────────────────────────────────────────────────────────────────


    async def _load_session(
        self,
        session_id: str,
        student_id: str,
    ) -> SessionSnapshot:

        session = (
            await self._session_repo
            .find_by_id_and_student(
                session_id,
                student_id,
            )
        )

        if session is None:

            raise SessionNotFoundError(session_id)

        return session


    def _guard_transition(
        self,
        session: SessionSnapshot,
        target_status: SessionStatus,
    ) -> None:

        try:

            validate_transition(
                session.status,
                target_status,
            )

        except StateMachineInvalidTransitionError as exc:

            raise InvalidStateTransitionError(
                exc.current_status,
                exc.target_status,
            ) from exc


    async def _publish_or_raise(
        self,
        topic: str,
        payload: dict,
        flow: str,
    ) -> str:

        try:

            return await self._kafka.publish(
                topic,
                payload,
            )

        except Exception as exc:

            raise KafkaUnavailableError(flow) from exc


    async def _commit_status_or_raise(
        self,
        session: SessionSnapshot,
        new_status: SessionStatus,
    ) -> None:

        updated = (
            await self._session_repo.update_status(
                str(session.id),
                new_status,
                session.version,
            )
        )

        if not updated:

            raise SessionUpdateConflictError(
                str(session.id)
            )


    # ──────────────────────────────────────────────────────────────────────
    # TIPSC
    # ──────────────────────────────────────────────────────────────────────


    async def trigger_tipsc(
        self,
        session_id: str,
        student_id: str,
    ) -> dict:

        session = await self._load_session(
            session_id,
            student_id,
        )

        if session.status in {
            SessionStatus.QUEUED,
            SessionStatus.PRE_EVAL,
            SessionStatus.VALIDATION_RUNNING,
            SessionStatus.ETHICS_RUNNING,
            SessionStatus.TIPSC_RUNNING,
        }:

            return {
                "session_id": str(session.id),
                "flow": "tipsc",
                "status": session.status.value,
                "correlation_id": session.correlation_id,
                "triggered_at": _now_iso(),
            }


        self._guard_transition(
            session,
            SessionStatus.QUEUED,
        )


        await self._commit_status_or_raise(
            session,
            SessionStatus.QUEUED,
        )


        correlation_id = _new_correlation_id()


        await self._session_repo.set_correlation_id(
            session_id,
            correlation_id,
        )


        await self._audit.log_event(
            session_id=session_id,
            event="TIPSC_TRIGGERED",
            actor=student_id,
            actor_role="student",
            metadata={
                "correlation_id": correlation_id,
            },
        )


        # Import here to avoid startup circular imports.
        from events import startup


        executor = startup.tipsc_executor_instance


        if executor is None:

            raise RuntimeError(
                "TIPSC executor is not initialized."
            )


        preeval_input = (
            session.preeval_input
            or {
                "problem_statement": session.problem_statement,
                "proposed_solution": session.idea,
            }
        )


        # Fire-and-forget.
        #
        # HTTP response returns immediately.
        # Pipeline continues independently.
        asyncio.create_task(
            executor.run(
                session_id=session_id,
                preeval_input=preeval_input,
            )
        )


        return {
            "session_id": str(session.id),
            "flow": "tipsc",
            "status": SessionStatus.QUEUED.value,
            "correlation_id": correlation_id,
            "triggered_at": _now_iso(),
        }


    # ──────────────────────────────────────────────────────────────────────
    # TIPSC FOLLOW-UP
    # ──────────────────────────────────────────────────────────────────────


    async def submit_followup_answer(
        self,
        session_id: str,
        student_id: str,
        answer: str,
    ) -> dict:

        session = await self._load_session(
            session_id,
            student_id,
        )


        if (
            session.status
            != SessionStatus.WAITING_FOR_FOUNDER
        ):

            raise InvalidStateTransitionError(
                session.status,
                SessionStatus.TIPSC_REEVALUATION,
            )


        if not session.pending_question:

            raise RuntimeError(
                "Session has no pending follow-up question."
            )


        self._guard_transition(
            session,
            SessionStatus.TIPSC_REEVALUATION,
        )


        from events import startup


        executor = startup.tipsc_executor_instance


        if executor is None:

            raise RuntimeError(
                "TIPSC executor is not initialized."
            )


        await self._audit.log_event(
            session_id=session_id,
            event="TIPSC_FOLLOWUP_ANSWERED",
            actor=student_id,
            actor_role="student",
            metadata={
                "turn": session.followup_turn,
                "question": session.pending_question,
            },
        )


        # Pipeline executor performs:
        #
        # 1. Save answer
        # 2. Append question/answer to history
        # 3. Set TIPSC_REEVALUATION
        # 4. Re-run TIPSC
        # 5. Ask another question OR complete TIPSC

        asyncio.create_task(
            executor.resume_after_followup(
                session_id=session_id,
                answer=answer,
            )
        )


        return {
            "session_id": str(session.id),
            "flow": "tipsc",
            "status": (
                SessionStatus
                .TIPSC_REEVALUATION
                .value
            ),
            "followup_turn": session.followup_turn,
            "submitted_at": _now_iso(),
        }


    # ──────────────────────────────────────────────────────────────────────
    # DFV
    # ──────────────────────────────────────────────────────────────────────


    async def trigger_dfv(
        self,
        session_id: str,
        student_id: str,
        dfv_inputs: dict,
    ) -> dict:

        session = await self._load_session(
            session_id,
            student_id,
        )

        if not session.tipsc:
            ready_for_dfv = False

        elif isinstance(session.tipsc, dict):
            ready_for_dfv = bool(
                session.tipsc.get(
                    "ready_for_dfv",
                    False,
                )
            )

        else:
            ready_for_dfv = bool(
                getattr(
                    session.tipsc,
                    "ready_for_dfv",
                    False,
                )
            )

        if not ready_for_dfv:
            raise DFVNotUnlockedError(session_id)

        self._guard_transition(
            session,
            SessionStatus.DFV_WAITING,
        )

        await self._session_repo.update_dfv_inputs(
            session_id,
            dfv_inputs,
        )

        correlation_id = _new_correlation_id()

        from models.schema import (
            DFVJobMessage,
            DFVJobPayload,
        )

        payload = DFVJobMessage(
            userSession_id=str(session.id),
            idea_name=session.idea,
            correlation_id=correlation_id,
            retry_count=0,
            payload=DFVJobPayload(
                desirability_context=dfv_inputs["desirability_context"],
                feasibility_context=dfv_inputs["feasibility_context"],
                viability_context=dfv_inputs["viability_context"],
            ),
        )

        # ------------------------------------------------------------
        # 1. Save correlation id FIRST
        # ------------------------------------------------------------
        await self._session_repo.set_correlation_id(
            session_id,
            correlation_id,
        )

        # ------------------------------------------------------------
        # 2. Update session status in Mongo BEFORE Kafka publish
        # ------------------------------------------------------------
        await self._commit_status_or_raise(
            session,
            SessionStatus.DFV_WAITING,
        )

        # ------------------------------------------------------------
        # 3. Publish job to Kafka
        # ------------------------------------------------------------
        await self._publish_or_raise(
            DFV_TOPIC,
            payload.model_dump(),
            "dfv",
        )

        # ------------------------------------------------------------
        # 4. Audit
        # ------------------------------------------------------------
        await self._audit.log_event(
            session_id=session_id,
            event="DFV_TRIGGERED",
            actor=student_id,
            actor_role="student",
            metadata={
                "correlation_id": correlation_id,
            },
        )

        return {
            "session_id": str(session.id),
            "flow": "dfv",
            "status": SessionStatus.DFV_WAITING.value,
            "correlation_id": correlation_id,
            "triggered_at": _now_iso(),
        }


    # ──────────────────────────────────────────────────────────────────────
    # DISCOVERY
    # ──────────────────────────────────────────────────────────────────────


    async def trigger_discovery(
        self,
        session_id: str,
        student_id: str,
        discovery_inputs: dict,
    ) -> dict:

        session = await self._load_session(
            session_id,
            student_id,
        )

        self._guard_transition(
            session,
            SessionStatus.DISCOVERY_WAITING,
        )

        # Persist the student's submitted Discovery form
        # (Implement update_discovery_inputs() in session_repo if it doesn't exist yet.)
        await self._session_repo.update_discovery_inputs(
            session_id,
            discovery_inputs,
        )

        correlation_id = _new_correlation_id()

        payload = DiscoveryJobMessage(
            userSession_id=str(session.id),
            correlation_id=correlation_id,
            retry_count=0,
            payload=DiscoveryJobPayload(**discovery_inputs),
        )

        #
        # IMPORTANT:
        # Persist state BEFORE publishing to Kafka.
        #

        await self._session_repo.set_correlation_id(
            session_id,
            correlation_id,
        )

        await self._commit_status_or_raise(
            session,
            SessionStatus.DISCOVERY_WAITING,
        )

        await self._publish_or_raise(
            DISCOVERY_TOPIC,
            payload.model_dump(),
            "discovery",
        )

        await self._audit.log_event(
            session_id=session_id,
            event="DISCOVERY_TRIGGERED",
            actor=student_id,
            actor_role="student",
            metadata={
                "correlation_id": correlation_id,
            },
        )

        return {
            "session_id": str(session.id),
            "flow": "discovery",
            "status": SessionStatus.DISCOVERY_WAITING.value,
            "correlation_id": correlation_id,
            "triggered_at": _now_iso(),
        }