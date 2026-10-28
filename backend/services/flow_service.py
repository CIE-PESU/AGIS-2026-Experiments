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
import hashlib
import json
import uuid

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from models.schema import (
    DFVJobMessage,
    DFVJobPayload,
    DiscoveryJobMessage,
    DiscoveryJobPayload,
    PMFJobMessage,
    PMFJobPayload,
)
from kafka.topics import KafkaTopic
from services.session_task_registry import register_session_task

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
PMF_TOPIC = KafkaTopic.USER_SESSION_PMF


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
        student_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> SessionSnapshot:

        if not student_id and not workspace_id:
            raise SessionNotFoundError(session_id)

        session = await self._session_repo.find_by_id(session_id)

        if session is None:
            raise SessionNotFoundError(session_id)

        if workspace_id:
            if session.workspace_id != workspace_id:
                raise SessionNotFoundError(session_id)
        elif student_id:
            if session.student_id != student_id:
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
        student_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> dict:

        session = await self._load_session(
            session_id,
            student_id=student_id,
            workspace_id=workspace_id,
        )

        if session.status in {
            SessionStatus.QUEUED,
            SessionStatus.PRE_EVAL,
            SessionStatus.VALIDATION_RUNNING,
            SessionStatus.REGULATORY_RUNNING,
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

        from events import startup
        executor = startup.tipsc_executor_instance
        if executor is None:
            raise RuntimeError("TIPSC executor is not initialized.")


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
            actor=student_id or (f"ws_{workspace_id}" if workspace_id else "system"),
            actor_role="student" if student_id else "mentor_workspace",
            metadata={
                "correlation_id": correlation_id,
            },
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
        
        register_session_task(session_id, asyncio.create_task(
            executor.run(
                session_id=session_id,
                preeval_input=preeval_input,
            )
        ))


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
        student_id: Optional[str] = None,
        answer: str = "",
        workspace_id: Optional[str] = None,
    ) -> dict:

        session = await self._load_session(
            session_id,
            student_id=student_id,
            workspace_id=workspace_id,
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


        # Pipeline executor performs:
        #
        # 1. Save answer
        # 2. Append question/answer to history
        # 3. Set TIPSC_REEVALUATION
        # 4. Re-run TIPSC
        # 5. Ask another question OR complete TIPSC

        claimed = await self._session_repo.submit_followup_answer(session_id, answer, session.version)
        if not claimed:
            raise SessionUpdateConflictError(session_id)
        await self._audit.log_event(
            session_id=session_id,
            event="TIPSC_FOLLOWUP_ANSWERED",
            actor=student_id or (f"ws_{workspace_id}" if workspace_id else "system"),
            actor_role="student" if student_id else "mentor_workspace",
            metadata={"turn": session.followup_turn, "question": session.pending_question},
        )
        register_session_task(session_id, asyncio.create_task(
            executor.resume_after_followup(session_id=session_id, answer=answer, claimed=True)
        ))


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


    async def trigger_dfv(self, session_id, student_id=None, dfv_inputs=None,
                          workspace_id=None, idempotency_key=None):
        from schemas.flow import DFVTriggerRequest
        inputs = DFVTriggerRequest(**(dfv_inputs or {})).model_dump()
        return await self._trigger_agent_flow("dfv", session_id, student_id, workspace_id, inputs, idempotency_key)

    async def trigger_discovery(self, session_id, student_id=None, discovery_inputs=None,
                                workspace_id=None, idempotency_key=None):
        inputs = DiscoveryJobPayload(**(discovery_inputs or {})).model_dump()
        return await self._trigger_agent_flow("discovery", session_id, student_id, workspace_id, inputs, idempotency_key)

    async def trigger_pmf(self, session_id, student_id=None, workspace_id=None, idempotency_key=None):
        return await self._trigger_agent_flow("pmf", session_id, student_id, workspace_id, None, idempotency_key)

    async def _trigger_agent_flow(self, flow, session_id, student_id, workspace_id, inputs, idempotency_key):
        session = await self._load_session(session_id, student_id, workspace_id)
        fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
        previous = (getattr(session, "flow_requests", None) or {}).get(flow)
        if idempotency_key and previous and previous.get("key") == idempotency_key:
            if previous["fingerprint"] != fingerprint:
                raise SessionUpdateConflictError(session_id)
            return previous["response"]

        waiting = SessionStatus(f"{flow}_waiting")
        running = SessionStatus(f"{flow}_running")
        if session.status in {waiting, running}:
            return {"session_id": session_id, "flow": flow, "status": session.status.value,
                    "correlation_id": session.correlation_id, "triggered_at": _now_iso()}
        self._guard_transition(session, waiting)
        if flow == "dfv":
            tipsc = session.tipsc
            ready = tipsc.get("ready_for_dfv", False) if isinstance(tipsc, dict) else getattr(tipsc, "ready_for_dfv", False)
            if not ready:
                raise DFVNotUnlockedError(session_id)
        if flow == "discovery":
            dfv = session.dfv.model_dump() if hasattr(session.dfv, "model_dump") else session.dfv or {}
            output = dfv.get("output") or dfv
            if (output.get("decision") or (output.get("final_decision") or {}).get("status")) != "GO":
                raise InvalidStateTransitionError(session.status, waiting)
        if flow == "pmf" and not session.discovery:
            raise InvalidStateTransitionError(session.status, waiting)

        correlation_id = _new_correlation_id()
        response = {"session_id": session_id, "flow": flow, "status": waiting.value,
                    "correlation_id": correlation_id, "triggered_at": _now_iso()}
        common = dict(userSession_id=session_id, correlation_id=correlation_id, retry_count=0)
        if flow == "dfv":
            payload = DFVJobMessage(**common, idea_name=session.idea, payload=DFVJobPayload(**inputs))
        elif flow == "discovery":
            payload = DiscoveryJobMessage(**common, payload=DiscoveryJobPayload(**inputs))
        else:
            def dump(value):
                return value.model_dump(mode="json") if hasattr(value, "model_dump") else value
            founder = session.preeval_input or {}
            payload = PMFJobMessage(**common, payload=PMFJobPayload(
                idea_name=session.idea or "", problem_statement=session.problem_statement or "",
                proposed_solution=session.idea or "", customer_segment=founder.get("customer_segment", ""),
                tipsc_summary=dump(session.tipsc), dfv_summary=dump(session.dfv),
                discovery_summary=dump(session.discovery),
            ))
        record = {"key": idempotency_key, "fingerprint": fingerprint, "response": response} if idempotency_key else None
        won = await self._session_repo.atomic_start_flow(
            session_id, flow, correlation_id, inputs, session.version, record,
        )
        if not won:
            raise SessionUpdateConflictError(session_id)
        try:
            await self._publish_or_raise(
                {"dfv": DFV_TOPIC, "discovery": DISCOVERY_TOPIC, "pmf": PMF_TOPIC}[flow],
                payload.model_dump(), flow,
            )
        except KafkaUnavailableError:
            await self._session_repo.update_flow_failure(
                session_id, SessionStatus(f"{flow}_failed"),
                {"flow": flow, "error_code": "KAFKA_UNAVAILABLE", "error_message": "Could not enqueue analysis. Please retry."},
                expected_version=session.version + 1, expected_status=waiting, correlation_id=correlation_id,
            )
            raise
        await self._audit.log_event(
            session_id=session_id, event=f"{flow.upper()}_TRIGGERED",
            actor=student_id or f"ws_{workspace_id}", actor_role="student" if student_id else "mentor_workspace",
            metadata={"correlation_id": correlation_id},
        )
        return response
