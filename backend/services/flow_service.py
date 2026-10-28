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
from datetime import UTC, datetime
from typing import Any, Protocol

from events import startup
from exceptions.base import PipelineUnavailableError
from kafka.topics import KafkaTopic
from models.schema import (
    DFVJobMessage,
    DFVJobPayload,
    DiscoveryJobMessage,
    DiscoveryJobPayload,
)
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

    preeval_input: dict[str, Any] | None = None

    tipsc: dict[str, Any] | None = None

    dfv: dict[str, Any] | None = None

    pending_question: str | None = None

    pending_answer: str | None = None

    followup_turn: int = 0

    followup_history: list[dict[str, Any]] | None = None

    correlation_id: str | None = None

    workspace_id: str | None = None
    flow_requests: dict | None = None

    @property
    def id(self) -> str:
        return self.session_id


# ─────────────────────────────────────────────────────────────────────────────
# Repository contract
# ─────────────────────────────────────────────────────────────────────────────


class SessionRepoProtocol(Protocol):
    async def find_by_id(self, session_id: str) -> Any: ...
    async def update_status(
        self, session_id: str, new_status: SessionStatus, expected_version: int
    ) -> bool: ...
    async def set_correlation_id(self, session_id: str, correlation_id: str) -> None: ...
    async def submit_followup_answer(
        self, session_id: str, answer: str, expected_version: int
    ) -> bool: ...
    async def atomic_start_dfv_flow(
        self,
        session_id: str,
        correlation_id: str,
        dfv_inputs: dict,
        request_record: dict | None = None,
        expected_version: int | None = None,
    ) -> bool: ...
    async def atomic_start_discovery_flow(
        self,
        session_id: str,
        correlation_id: str,
        discovery_inputs: dict,
        request_record: dict | None = None,
        expected_version: int | None = None,
    ) -> bool: ...
    async def update_flow_failure(
        self,
        session_id: str,
        new_status: SessionStatus,
        failure_metadata: dict,
        expected_version: int | None = None,
        correlation_id: str | None = None,
    ) -> bool: ...


class KafkaProducerProtocol(Protocol):
    async def publish(
        self,
        topic: str,
        payload: dict[str, Any],
    ) -> str: ...


class AuditServiceProtocol(Protocol):
    async def log_event(
        self,
        session_id: str,
        event: str,
        actor: str,
        actor_role: str,
        metadata: dict[str, Any],
    ) -> None: ...


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _now_iso() -> str:

    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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

    def _request_record(self, session, flow, key, inputs):
        if not key:
            return None, None
        slot = hashlib.sha256(f"{flow}:{key}".encode()).hexdigest()
        digest = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
        existing = (getattr(session, "flow_requests", None) or {}).get(slot)
        if existing:
            if existing["digest"] != digest:
                raise SessionUpdateConflictError(str(session.id))
            return None, existing["response"]
        return {"slot": slot, "digest": digest}, None

    # ──────────────────────────────────────────────────────────────────────
    # Shared helpers
    # ──────────────────────────────────────────────────────────────────────

    async def _load_session(
        self,
        session_id: str,
        student_id: str | None = None,
        workspace_id: str | None = None,
    ) -> SessionSnapshot:

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

        updated = await self._session_repo.update_status(
            str(session.id),
            new_status,
            session.version,
        )

        if not updated:
            raise SessionUpdateConflictError(str(session.id))

    # ──────────────────────────────────────────────────────────────────────
    # TIPSC
    # ──────────────────────────────────────────────────────────────────────

    async def trigger_tipsc(
        self,
        session_id: str,
        student_id: str | None = None,
        workspace_id: str | None = None,
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

        executor = startup.tipsc_executor_instance
        if executor is None:
            raise PipelineUnavailableError()

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

        # Import here to avoid startup circular imports.

        executor = startup.tipsc_executor_instance

        if executor is None:
            raise PipelineUnavailableError()

        preeval_input = session.preeval_input or {
            "problem_statement": session.problem_statement,
            "proposed_solution": session.idea,
        }

        # Fire-and-forget.
        #
        # HTTP response returns immediately.
        # Pipeline continues independently.

        from services.session_task_registry import register_session_task

        task = asyncio.create_task(
            executor.run(
                session_id=session_id,
                preeval_input=preeval_input,
            )
        )
        register_session_task(session_id, task)

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
        student_id: str | None = None,
        answer: str = "",
        workspace_id: str | None = None,
    ) -> dict:

        session = await self._load_session(
            session_id,
            student_id=student_id,
            workspace_id=workspace_id,
        )

        if session.status != SessionStatus.WAITING_FOR_FOUNDER:
            raise InvalidStateTransitionError(
                session.status,
                SessionStatus.TIPSC_REEVALUATION,
            )

        if not session.pending_question:
            raise RuntimeError("Session has no pending follow-up question.")

        self._guard_transition(
            session,
            SessionStatus.TIPSC_REEVALUATION,
        )

        executor = startup.tipsc_executor_instance

        if executor is None:
            raise PipelineUnavailableError()

        claimed = await self._session_repo.submit_followup_answer(
            session_id=session_id,
            answer=answer.strip(),
            expected_version=session.version,
        )
        if not claimed:
            raise SessionUpdateConflictError(session_id)

        await self._audit.log_event(
            session_id=session_id,
            event="TIPSC_FOLLOWUP_ANSWERED",
            actor=student_id or (f"ws_{workspace_id}" if workspace_id else "system"),
            actor_role="student" if student_id else "mentor_workspace",
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

        from services.session_task_registry import register_session_task

        task = asyncio.create_task(
            executor.resume_after_followup(
                session_id=session_id,
                answer=answer,
                claimed=True,
            )
        )
        register_session_task(session_id, task)

        return {
            "session_id": str(session.id),
            "flow": "tipsc",
            "status": (SessionStatus.TIPSC_REEVALUATION.value),
            "followup_turn": session.followup_turn,
            "submitted_at": _now_iso(),
        }

    # ──────────────────────────────────────────────────────────────────────
    # DFV
    # ──────────────────────────────────────────────────────────────────────

    async def trigger_dfv(
        self,
        session_id: str,
        student_id: str | None = None,
        dfv_inputs: dict | None = None,
        workspace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict:

        dfv_inputs = dfv_inputs or {}
        session = await self._load_session(
            session_id,
            student_id=student_id,
            workspace_id=workspace_id,
        )
        record, replay = self._request_record(session, "dfv", idempotency_key, dfv_inputs)
        if replay:
            return replay

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

        if session.status == SessionStatus.DFV_COMPLETED:
            previous = session.dfv
            if not isinstance(previous, dict):
                previous = getattr(previous, "output", None) or {}
            output = previous.get("output") or previous
            final_decision = output.get("final_decision") or {}
            if not isinstance(final_decision, dict):
                final_decision = getattr(final_decision, "model_dump", lambda: {})()
            decision = output.get("decision") or final_decision.get("status")
            if decision != "NO-GO":
                raise InvalidStateTransitionError(session.status, SessionStatus.DFV_WAITING)

        correlation_id = _new_correlation_id()
        if record:
            record["response"] = {
                "session_id": str(session.id),
                "flow": "dfv",
                "status": "dfv_waiting",
                "correlation_id": correlation_id,
                "triggered_at": _now_iso(),
            }

        # Atomic CAS: Transition status to DFV_WAITING and set correlation_id in a single Mongo write.
        cas_won = await self._session_repo.atomic_start_dfv_flow(
            session_id=session_id,
            correlation_id=correlation_id,
            dfv_inputs=dfv_inputs,
            expected_version=session.version,
            **({"request_record": record} if record else {}),
        )

        if not cas_won:
            # CAS lost — session is already in DFV_WAITING or DFV_RUNNING! Return active state safely.
            current = await self._load_session(
                session_id, student_id=student_id, workspace_id=workspace_id
            )
            _, replay = self._request_record(current, "dfv", idempotency_key, dfv_inputs)
            if replay:
                return replay
            if current.status not in {SessionStatus.DFV_WAITING, SessionStatus.DFV_RUNNING}:
                raise InvalidStateTransitionError(current.status, SessionStatus.DFV_WAITING)
            return {
                "session_id": str(current.id),
                "flow": "dfv",
                "status": current.status.value,
                "correlation_id": current.correlation_id or correlation_id,
                "triggered_at": _now_iso(),
            }

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

        # Publish job to Kafka
        try:
            await self._publish_or_raise(
                DFV_TOPIC,
                payload.model_dump(),
                "dfv",
            )
        except KafkaUnavailableError:
            await self._session_repo.update_flow_failure(
                session_id,
                SessionStatus.DFV_FAILED,
                {
                    "flow": "dfv",
                    "error_code": "KAFKA_UNAVAILABLE",
                    "error_message": "Could not start DFV analysis.",
                },
                correlation_id=correlation_id,
            )
            raise

        # Audit
        await self._audit.log_event(
            session_id=session_id,
            event="DFV_TRIGGERED",
            actor=student_id or (f"ws_{workspace_id}" if workspace_id else "system"),
            actor_role="student" if student_id else "mentor_workspace",
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
        student_id: str | None = None,
        discovery_inputs: dict | None = None,
        workspace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict:

        discovery_inputs = discovery_inputs or {}
        session = await self._load_session(
            session_id,
            student_id=student_id,
            workspace_id=workspace_id,
        )
        record, replay = self._request_record(
            session, "discovery", idempotency_key, discovery_inputs
        )
        if replay:
            return replay

        previous = session.dfv
        if previous is not None and not isinstance(previous, dict):
            previous = previous.model_dump()
        output = (previous or {}).get("output") or previous or {}
        decision = output.get("decision") or (output.get("final_decision") or {}).get("status")
        if decision != "GO":
            raise InvalidStateTransitionError(session.status, SessionStatus.DISCOVERY_WAITING)

        correlation_id = _new_correlation_id()
        if record:
            record["response"] = {
                "session_id": str(session.id),
                "flow": "discovery",
                "status": "discovery_waiting",
                "correlation_id": correlation_id,
                "triggered_at": _now_iso(),
            }

        # Atomic CAS: Transition status to DISCOVERY_WAITING and set correlation_id in a single Mongo write.
        cas_won = await self._session_repo.atomic_start_discovery_flow(
            session_id=session_id,
            correlation_id=correlation_id,
            discovery_inputs=discovery_inputs,
            expected_version=session.version,
            **({"request_record": record} if record else {}),
        )

        if not cas_won:
            # CAS lost — session is already in DISCOVERY_WAITING or DISCOVERY_RUNNING! Return active state safely.
            current = await self._load_session(
                session_id, student_id=student_id, workspace_id=workspace_id
            )
            _, replay = self._request_record(
                current, "discovery", idempotency_key, discovery_inputs
            )
            if replay:
                return replay
            if current.status not in {
                SessionStatus.DISCOVERY_WAITING,
                SessionStatus.DISCOVERY_RUNNING,
            }:
                raise InvalidStateTransitionError(current.status, SessionStatus.DISCOVERY_WAITING)
            return {
                "session_id": str(current.id),
                "flow": "discovery",
                "status": current.status.value,
                "correlation_id": current.correlation_id or correlation_id,
                "triggered_at": _now_iso(),
            }

        payload = DiscoveryJobMessage(
            userSession_id=str(session.id),
            correlation_id=correlation_id,
            retry_count=0,
            payload=DiscoveryJobPayload(**discovery_inputs),
        )

        try:
            await self._publish_or_raise(
                DISCOVERY_TOPIC,
                payload.model_dump(),
                "discovery",
            )
        except KafkaUnavailableError:
            await self._session_repo.update_flow_failure(
                session_id,
                SessionStatus.DISCOVERY_FAILED,
                {
                    "flow": "discovery",
                    "error_code": "KAFKA_UNAVAILABLE",
                    "error_message": "Could not start Customer Discovery.",
                },
                correlation_id=correlation_id,
            )
            raise

        await self._audit.log_event(
            session_id=session_id,
            event="DISCOVERY_TRIGGERED",
            actor=student_id or (f"ws_{workspace_id}" if workspace_id else "system"),
            actor_role="student" if student_id else "mentor_workspace",
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
