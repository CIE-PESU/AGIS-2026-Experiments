"""
api/v1/flows.py — Flow trigger endpoints.

POST /sessions/{session_id}/trigger/tipsc
POST /sessions/{session_id}/trigger/dfv
POST /sessions/{session_id}/trigger/discovery

These endpoints are thin wrappers. All state-machine logic lives in FlowService.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.core.constants import UserRole
from app.dependencies.auth import get_current_user, require_role
from app.exceptions.base import (
    DFVNotUnlockedError,
    FlowAlreadyRunningError,
    InvalidStateTransitionError,
    KafkaPublishError,
    SessionNotFoundError,
)
from app.repositories.session_repo import session_repo
from app.schemas.auth import CurrentUser
from app.schemas.flow import DFVTriggerRequest, FlowTriggerResponse
from app.services.audit_service import audit_service
from app.services.flow_service import FlowService
from app.kafka.producer import kafka_producer
from app.utils.response import success_response

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
            from app.kafka.payloads import TIPSCEventPayload, DFVEventPayload, DiscoveryEventPayload
            from app.kafka.topics import KafkaTopic

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

            return await kafka_producer.publish(topic=topic, payload=payload_obj)

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
):
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
):
    flow_service = _get_flow_service()
    result = await flow_service.trigger_discovery(session_id, current_user.user_id)
    return result