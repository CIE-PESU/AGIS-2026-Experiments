"""
Flow trigger service — TIPSC / DFV / Discovery gate.

Depends on three collaborators, injected via the constructor so this
service can be fully unit tested without a real MongoDB or Kafka broker:

- session_repo:   find_by_id_and_student(), update_status(),
                   and update_dfv_inputs() (see note below)
                   -> repositories/session_repo.py, Bhavesh (B-04)
- kafka_producer: publish(topic, payload) -> correlation_id
                   -> kafka/producer.py, Vijay (B-06)
- audit_service:  log_event(session_id, event, actor, actor_role, metadata)
                   -> services/audit_service.py, Palash (B-08, Day 2)

None of those modules are imported directly. The Protocol classes below
define exactly what this service needs from each — nothing more. Wire the
real implementations in at the FastAPI dependency layer (api/v1/flows.py)
once those branches are on develop-backend.

Coordination flag for Bhavesh: session_repo's Day 1 method list
(find_by_id, find_by_id_and_student, find_by_student, find_by_teams,
update_status, update_flow_output, archive, find_active_by_student)
doesn't include anything for persisting DFV context inputs
(desirability/feasibility/viability strings) onto the session document
before it moves to DFV_WAITING. I've added `update_dfv_inputs` to the
protocol below as the method this service expects — needs a real
implementation on your side, or point me to whichever method you'd
rather I call instead.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from kafka.topics import KafkaTopic
from services.flow_exceptions import (
    DFVNotUnlockedError,
    FlowAlreadyRunningError,
    InvalidStateTransitionError,
    KafkaUnavailableError,
    SessionNotFoundError,
    SessionUpdateConflictError,
)
from state_machine.exceptions import (
    InvalidStateTransitionError as StateMachineInvalidTransitionError,
)
from state_machine.states import RUNNING_STATES, SessionStatus
from state_machine.validator import validate_transition

# Re-export as aliases for backwards compatibility with existing tests
TIPSC_TOPIC = KafkaTopic.USER_SESSION_TIPSC
DFV_TOPIC = KafkaTopic.USER_SESSION_DFV
DISCOVERY_TOPIC = KafkaTopic.USER_SESSION_DISCOVERY



# ---------------------------------------------------------------------------
# Typing-only placeholders for cross-branch collaborators. Replace with real
# imports once B-04 / B-06 / B-08 land on develop-backend.
# ---------------------------------------------------------------------------


@dataclass
class SessionSnapshot:
    """
    Minimal shape of a session document that this service reads/writes.
    NOT the real ODM model — models/session.py (Bhavesh) is the source of
    truth. Only the fields FlowService touches are modeled here.
    """

    session_id: str
    student_id: str
    team_id: str
    status: SessionStatus
    version: int
    problem_statement: str
    idea: str
    tipsc: Optional[dict] = None  # {"ready_for_dfv": bool, "reasoning": str, ...}
    dfv: Optional[dict] = None  # {"summary": str, ...}
    correlation_id: Optional[str] = None

    @property
    def id(self) -> str:
        return self.session_id


class SessionRepoProtocol(Protocol):
    async def find_by_id_and_student(
        self, session_id: str, student_id: str
    ) -> Optional[SessionSnapshot]: ...

    async def update_status(
        self, session_id: str, new_status: SessionStatus, expected_version: int
    ) -> bool: ...

    async def set_correlation_id(self, session_id: str, correlation_id: str) -> None: ...

    async def update_dfv_inputs(self, session_id: str, dfv_inputs: dict) -> bool:
        """Not in Bhavesh's documented method list yet — see module docstring."""
        ...


class KafkaProducerProtocol(Protocol):
    async def publish(self, topic: str, payload: dict[str, Any]) -> str:
        """Returns correlation_id on success; raises on failure after retries."""
        ...


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


def _new_correlation_id() -> str:
    return f"cor_{uuid.uuid4().hex}"


def _base_kafka_payload(session: SessionSnapshot, flow: str, correlation_id: str) -> dict:
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

    # -- shared helpers ----------------------------------------------------

    async def _load_session(self, session_id: str, student_id: str) -> SessionSnapshot:
        session = await self._session_repo.find_by_id_and_student(session_id, student_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    def _guard_transition(self, session: SessionSnapshot, target_status: SessionStatus) -> None:
        """
        Defense-in-depth: re-check against the canonical state machine map
        even though the flow-specific checks below should already have
        caught anything invalid. Translates the pure-logic exception from
        state_machine/ into this module's API-facing one.
        """
        try:
            validate_transition(session.status, target_status)
        except StateMachineInvalidTransitionError as exc:
            raise InvalidStateTransitionError(
                exc.current_status, exc.target_status
            ) from exc

    async def _publish_or_raise(self, topic: str, payload: dict, flow: str) -> str:
        try:
            return await self._kafka.publish(topic, payload)
        except Exception as exc:  # noqa: BLE001 — deliberately broad: any producer
            # failure (including the real KafkaPublishError once B-06 lands)
            # becomes a 503 at this layer.
            raise KafkaUnavailableError(flow) from exc

    async def _commit_status_or_raise(
        self, session: SessionSnapshot, new_status: SessionStatus
    ) -> None:
        updated = await self._session_repo.update_status(
            str(session.id), new_status, session.version
        )
        if not updated:
            raise SessionUpdateConflictError(str(session.id))

    # -- public API ----------------------------------------------------------

    async def trigger_tipsc(self, session_id: str, student_id: str) -> dict:
        """
        Manual retry path for TIPSC — normally auto-triggered on session
        creation. Idempotent: calling this on an already-QUEUED session is
        a no-op, it does not re-publish.
        """
        session = await self._load_session(session_id, student_id)



        self._guard_transition(session, SessionStatus.QUEUED)

        correlation_id = _new_correlation_id()
        payload = _base_kafka_payload(session, "tipsc", correlation_id)
        payload["problem_statement"] = session.problem_statement
        payload["idea"] = session.idea

        await self._publish_or_raise(TIPSC_TOPIC, payload, "tipsc")
        await self._commit_status_or_raise(session, SessionStatus.QUEUED)
        await self._session_repo.set_correlation_id(session_id, correlation_id)
        await self._audit.log_event(
            session_id=session_id,
            event="TIPSC_TRIGGERED",
            actor=student_id,
            actor_role="student",
            metadata={"correlation_id": correlation_id},
        )

        return {
            "session_id": str(session.id),
            "flow": "tipsc",
            "status": SessionStatus.QUEUED.value,
            "correlation_id": correlation_id,
            "triggered_at": _now_iso(),
        }

    async def trigger_dfv(
        self, session_id: str, student_id: str, dfv_inputs: dict
    ) -> dict:
        session = await self._load_session(session_id, student_id)



        if not session.tipsc:
            ready_for_dfv = False
        elif isinstance(session.tipsc, dict):
            ready_for_dfv = bool(session.tipsc.get("ready_for_dfv", False))
        else:
            ready_for_dfv = bool(getattr(session.tipsc, "ready_for_dfv", False))
        if not ready_for_dfv:
            raise DFVNotUnlockedError(session_id)

        self._guard_transition(session, SessionStatus.DFV_WAITING)

        await self._session_repo.update_dfv_inputs(session_id, dfv_inputs)

        correlation_id = _new_correlation_id()
        payload = _base_kafka_payload(session, "dfv", correlation_id)
        payload["problem_statement"] = session.problem_statement
        payload["idea"] = session.idea
        payload.update(dfv_inputs)  # desirability_context, feasibility_context, viability_context

        await self._publish_or_raise(DFV_TOPIC, payload, "dfv")
        await self._commit_status_or_raise(session, SessionStatus.DFV_WAITING)
        await self._session_repo.set_correlation_id(session_id, correlation_id)
        await self._audit.log_event(
            session_id=session_id,
            event="DFV_TRIGGERED",
            actor=student_id,
            actor_role="student",
            metadata={"correlation_id": correlation_id},
        )

        return {
            "session_id": str(session.id),
            "flow": "dfv",
            "status": SessionStatus.DFV_WAITING.value,
            "correlation_id": correlation_id,
            "triggered_at": _now_iso(),
        }

    async def trigger_discovery(self, session_id: str, student_id: str) -> dict:
        session = await self._load_session(session_id, student_id)



        self._guard_transition(session, SessionStatus.DISCOVERY_WAITING)

        correlation_id = _new_correlation_id()
        payload = _base_kafka_payload(session, "discovery", correlation_id)
        payload["problem_statement"] = session.problem_statement
        payload["idea"] = session.idea
        if not session.tipsc:
            payload["tipsc_summary"] = ""
        elif isinstance(session.tipsc, dict):
            payload["tipsc_summary"] = session.tipsc.get("reasoning", "")
        else:
            payload["tipsc_summary"] = getattr(session.tipsc, "reasoning", "")

        if not session.dfv:
            payload["dfv_summary"] = ""
        elif isinstance(session.dfv, dict):
            payload["dfv_summary"] = session.dfv.get("summary", "")
        else:
            payload["dfv_summary"] = getattr(session.dfv, "summary", "")

        await self._publish_or_raise(DISCOVERY_TOPIC, payload, "discovery")
        await self._commit_status_or_raise(session, SessionStatus.DISCOVERY_WAITING)
        await self._session_repo.set_correlation_id(session_id, correlation_id)
        await self._audit.log_event(
            session_id=session_id,
            event="DISCOVERY_TRIGGERED",
            actor=student_id,
            actor_role="student",
            metadata={"correlation_id": correlation_id},
        )

        return {
            "session_id": str(session.id),
            "flow": "discovery",
            "status": SessionStatus.DISCOVERY_WAITING.value,
            "correlation_id": correlation_id,
            "triggered_at": _now_iso(),
        }