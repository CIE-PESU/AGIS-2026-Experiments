"""
api/v1/flows.py — Flow trigger endpoints.

POST /sessions/{session_id}/trigger/tipsc
POST /sessions/{session_id}/trigger/dfv
POST /sessions/{session_id}/trigger/discovery

These endpoints are thin wrappers. All state-machine logic lives in FlowService.
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Request, status, BackgroundTasks, Header

from core.constants import UserRole
from dependencies.auth import get_current_user, require_role
from exceptions.base import (
    DFVNotUnlockedError,
    FlowAlreadyRunningError,
    InvalidStateTransitionError,
    KafkaPublishError,
    SessionNotFoundError,
)
from repositories.session_repo import session_repo
from schemas.auth import CurrentUser
from schemas.flow import DFVTriggerRequest, DiscoveryTriggerRequest, FlowTriggerResponse, FollowupAnswerRequest
from services.audit_service import audit_service
from services.flow_service import FlowService
from kafka.producer import kafka_producer
from utils.object_id import validate_object_id
from utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Flows"])


def _get_flow_service() -> FlowService:
    """
    Construct a FlowService with the real singleton dependencies.
    Called via FastAPI's Depends() — evaluated per-request but the
    underlying singletons (session_repo, kafka_producer, audit_service)
    are module-level singletons so no overhead.
    """

    # Adapt the kafka_producer to the KafkaProducerProtocol interface.
    # FlowService expects publish(topic, payload_dict) -> str,
    # but our KafkaProducerClient.publish(topic, payload: BaseModel) -> str.
    # We wrap it to handle both dict and BaseModel payloads.
    class KafkaAdaptor:
        async def publish(self, topic: str, payload: dict) -> str:
            from pydantic import BaseModel
            from kafka.payloads import TIPSCEventPayload, DFVEventPayload, DiscoveryEventPayload
            from kafka.topics import KafkaTopic

            # Determine the correct payload model based on topic
            topic_to_model = {
                KafkaTopic.USER_SESSION_TIPSC: TIPSCEventPayload,
                KafkaTopic.USER_SESSION_DFV: DFVEventPayload,
                KafkaTopic.USER_SESSION_DISCOVERY: DiscoveryEventPayload,
            }
            model_cls = topic_to_model.get(topic)
            if model_cls:
                payload_obj = model_cls(**payload)
            else:
                # Fallback: pass raw dict (shouldn't happen in normal flow)
                payload_obj = payload  # type: ignore[assignment]
            return await kafka_producer.publish(topic=topic, payload=payload_obj)  # type: ignore[arg-type]

    # Adapt the audit_service to the AuditServiceProtocol interface
    class AuditAdaptor:
        async def log_event(
            self,
            session_id: str,
            event: str,
            actor: str,
            actor_role: str,
            metadata: dict,
        ) -> None:
            await audit_service.log_event(
                session_id=session_id,
                event=event,
                actor=actor,
                actor_role=actor_role,
                metadata=metadata,
            )

    return FlowService(
        session_repo=session_repo,  # type: ignore[arg-type]
        kafka_producer=KafkaAdaptor(),  # type: ignore[arg-type]
        audit_service=AuditAdaptor(),  # type: ignore[arg-type]
    )


@router.post(
    "/{session_id}/trigger/tipsc",
    response_model=FlowTriggerResponse,
    status_code=status.HTTP_200_OK,
    summary="Manually trigger TIPSC evaluation",
    description=(
        "Manual retry path for TIPSC — normally auto-triggered when a session is created. "
        "Idempotent: calling this on an already-QUEUED session returns current state without re-publishing."
    ),
)
async def trigger_tipsc(
    request: Request,
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.STUDENT))],
):
    validate_object_id(session_id)
    flow_service = _get_flow_service()
    result = await flow_service.trigger_tipsc(session_id, current_user.user_id)
    return result


@router.post(
    "/{session_id}/trigger/dfv",
    response_model=FlowTriggerResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger DFV evaluation",
    description=(
        "Submits student-provided context strings and publishes to the DFV Kafka topic. "
        "Requires TIPSC to have completed with ready_for_dfv=True. "
        "Stores desirability, feasibility, and viability context on the session."
    ),
)
async def trigger_dfv(
    request: Request,
    session_id: str,
    body: DFVTriggerRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.STUDENT))],
    idempotency_key: Annotated[
        Optional[str],
        Header(alias="Idempotency-Key", description="UUID4. Prevents duplicate triggers on retry."),
    ] = None,
):
    validate_object_id(session_id)
    
    # If an Idempotency-Key is provided, check for a duplicate in-flight trigger
    if idempotency_key:
        session = await session_repo.find_by_id(session_id)
        if session and session.correlation_id and session.status == "dfv_waiting":
            # A trigger already fired and is in-flight — return current state
            return {
                "session_id": session_id,
                "flow": "dfv",
                "status": session.status.value,
                "correlation_id": session.correlation_id,
                "triggered_at": session.updated_at.isoformat() if session.updated_at else "",
            }
            
    flow_service = _get_flow_service()
    result = await flow_service.trigger_dfv(
        session_id, current_user.user_id, body.model_dump()
    )
    return result


@router.post(
    "/{session_id}/trigger/discovery",
    response_model=FlowTriggerResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Discovery (customer interview plan)",
    description=(
        "Triggers the Discovery phase after DFV has completed. "
        "Publishes to the userSession.discovery Kafka topic."
    ),
)
async def trigger_discovery(
    request: Request,
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.STUDENT))],
    body: DiscoveryTriggerRequest = DiscoveryTriggerRequest(),
    idempotency_key: Annotated[
        Optional[str],
        Header(alias="Idempotency-Key", description="UUID4. Prevents duplicate triggers on retry."),
    ] = None,
):
    validate_object_id(session_id)
    
    # If an Idempotency-Key is provided, check for a duplicate in-flight trigger
    if idempotency_key:
        session = await session_repo.find_by_id(session_id)
        if session and session.correlation_id and session.status == "discovery_waiting":
            # A trigger already fired and is in-flight — return current state
            return {
                "session_id": session_id,
                "flow": "discovery",
                "status": session.status.value,
                "correlation_id": session.correlation_id,
                "triggered_at": session.updated_at.isoformat() if session.updated_at else "",
            }

    flow_service = _get_flow_service()
    result = await flow_service.trigger_discovery(session_id, current_user.user_id)
    return result


@router.post(
    "/user/{student_id}/followup",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit founder answer to TIPSC followup question",
    description=(
        "Writes the founder's answer to the pending question and triggers the followup Kafka event to resume TIPSC."
    ),
)
async def submit_followup(
    request: Request,
    student_id: str,
    body: FollowupAnswerRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.STUDENT))],
):
    # Ensure students can only submit for themselves
    if current_user.user_id != student_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot submit followup for another user.")

    # We need to find the active session for this student that is WAITING_FOR_FOUNDER
    # and update it. Since FlowService expects session_id, let's fetch it first.
    # Actually, we should put this logic in FlowService.
    flow_service = _get_flow_service()
    
    # We need to add a method to FlowService to handle this, or do it here manually for the integration.
    # We will do it here by calling session_repo to get the active session.
    session = await session_repo.get_active_session_by_user(student_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session waiting for founder.")

    session_id = str(session["_id"])
    
    # Update DB with pending answer and set status to tipsc_running
    session_version = session.get("version", 0)
    updated = await session_repo.submit_followup_answer(session_id, body.answer, session_version)
    if not updated:
        from fastapi import HTTPException
        raise HTTPException(409, "Session was concurrently modified. Please retry.")

    try:
        from events.startup import tipsc_executor_instance
        if not tipsc_executor_instance:
            raise RuntimeError("TIPSC Executor not initialized.")
        background_tasks.add_task(tipsc_executor_instance.resume_after_followup, session_id, body.answer)
    except Exception as exc:
        logger.error(
            "TIPSC resume dispatch failed for session_id=%s | error=%s",
            session_id,
            exc,
            exc_info=True,
        )
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Failed to dispatch TIPSC resume task.")

    return {"status": "accepted", "session_id": session_id}