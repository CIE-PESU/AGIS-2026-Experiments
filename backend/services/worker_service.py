import logging
from typing import Any
from fastapi import BackgroundTasks
from pydantic import ValidationError

from exceptions.session import (
    SessionNotFoundError,
    InvalidStateTransitionError,
)
from exceptions.base import (
    CorrelationIDMismatchError,
    InvalidOutputSchemaError,
)
from models.session import TIPSCOutput, DFVOutput, DiscoveryOutput, PMFOutput
from models.audit import AuditEvent
from repositories.session_repo import session_repo
from services.audit_service import audit_service
from state_machine.states import SessionStatus, TERMINAL_STATES
from state_machine.validator import validate_transition

logger = logging.getLogger(__name__)

class WorkerService:
    async def accept_flow_output(
        self,
        session_id: str,
        flow: str,
        correlation_id: str,
        output: dict[str, Any],
        duration_seconds: float,
        worker_id: str,
        background_tasks: BackgroundTasks,
        status: str = "success", # From prompt, but not heavily used.
    ) -> dict:
        session = await session_repo.find_by_id(session_id)
        if not session:
            raise SessionNotFoundError()

        # --- IDEMPOTENCY CHECK ---
        # If the session already has this exact correlation_id stored in the flow's sub-field,
        # a previous delivery already processed this message. Safe to no-op.
        if session.correlation_id == correlation_id:
            # Check if the target flow field is already in a terminal state
            flow_data = getattr(session, flow, None)
            if flow_data is not None:
                existing_status = getattr(flow_data, "status", None)
                if existing_status in ("done", "completed"):
                    logger.info(
                        "Idempotency hit — skipping duplicate worker output | "
                        "session_id=%s flow=%s correlation_id=%s",
                        session_id, flow, correlation_id,
                    )
                    return {"status": "duplicate", "message": f"{flow} output already applied."}
        # --- END IDEMPOTENCY CHECK ---
        
        if session.correlation_id != correlation_id:
            raise CorrelationIDMismatchError()
            
        if session.status in TERMINAL_STATES:
            raise InvalidStateTransitionError(
                current_status=session.status,
                target_status=session.status, # any
                message="Cannot update a terminal session."
            )
            
        if not output:
            raise InvalidOutputSchemaError("Output cannot be empty.")
            
        if flow == "tipsc":
            try:
                parsed_output = TIPSCOutput(**output)
                target_status = SessionStatus.TIPSC_COMPLETED
                audit_event = AuditEvent.TIPSC_COMPLETED
            except ValidationError as e:
                raise InvalidOutputSchemaError(f"Invalid TIPSC output schema: {e}")
        elif flow == "dfv":
            try:
                parsed_output = DFVOutput(**output)
                target_status = SessionStatus.DFV_COMPLETED
                audit_event = AuditEvent.DFV_COMPLETED
            except ValidationError as e:
                raise InvalidOutputSchemaError(f"Invalid DFV output schema: {e}")
        elif flow == "discovery":
            try:
                parsed_output = DiscoveryOutput(**output)
                target_status = SessionStatus.COMPLETED
                audit_event = AuditEvent.DISCOVERY_COMPLETED
            except ValidationError as e:
                raise InvalidOutputSchemaError(f"Invalid Discovery output schema: {e}")
        elif flow == "pmf":
            try:
                parsed_output = PMFOutput(**output)
                target_status = SessionStatus.PMF_COMPLETED
                audit_event = AuditEvent.PMF_COMPLETED
            except ValidationError as e:
                raise InvalidOutputSchemaError(f"Invalid PMF output schema: {e}")
        else:
            raise InvalidOutputSchemaError(f"Unknown flow: {flow}")

        validate_transition(session.status, target_status)
        
        updated = await session_repo.update_flow_output(
            session_id=session_id,
            flow=flow,
            output=parsed_output.model_dump(),
            new_status=target_status,
            expected_version=session.version,
        )
        
        if not updated:
            raise InvalidStateTransitionError(message="Concurrent update detected. Output rejected.")
            
        background_tasks.add_task(
            audit_service.log_event,
            event=audit_event,
            actor=worker_id,
            actor_role="worker",
            session_id=session_id,
            metadata={"duration_seconds": duration_seconds, "flow": flow}
        )
        
        return {"status": "success", "message": f"{flow} output accepted."}


    async def accept_flow_failure(
        self,
        session_id: str,
        flow: str,
        correlation_id: str,
        error_code: str,
        error_message: str,
        retry_count: int,
        background_tasks: BackgroundTasks,
    ) -> dict:
        session = await session_repo.find_by_id(session_id)
        if not session:
            raise SessionNotFoundError()
            
        if session.correlation_id != correlation_id:
            raise CorrelationIDMismatchError()
            
        if flow == "tipsc":
            target_status = SessionStatus.TIPSC_FAILED
            audit_event = AuditEvent.TIPSC_FAILED
        elif flow == "dfv":
            target_status = SessionStatus.DFV_FAILED
            audit_event = AuditEvent.DFV_FAILED
        elif flow == "discovery":
            target_status = SessionStatus.DISCOVERY_FAILED
            audit_event = AuditEvent.DISCOVERY_FAILED
        elif flow == "pmf":
            target_status = SessionStatus.PMF_FAILED
            audit_event = AuditEvent.PMF_FAILED
        else:
            raise ValueError(f"Unknown flow: {flow}")
            
        validate_transition(session.status, target_status)
        
        failure_metadata = {
            "flow": flow,
            "error_code": error_code,
            "error_message": error_message,
            "retry_count": retry_count,
        }
        
        updated = await session_repo.update_flow_failure(
            session_id=session_id,
            new_status=target_status,
            failure_metadata=failure_metadata,
        )
        
        if not updated:
            raise InvalidStateTransitionError(message="Concurrent update detected. Failure rejected.")
            
        background_tasks.add_task(
            audit_service.log_event,
            event=audit_event,
            actor="worker", # typically worker_id, but it's not in the request schema
            actor_role="worker",
            session_id=session_id,
            metadata={"error_code": error_code, "error_message": error_message}
        )
        
        return {"status": "success", "message": f"{flow} failure accepted."}

worker_service = WorkerService()
