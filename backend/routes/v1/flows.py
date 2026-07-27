"""
api/v1/flows.py — Flow trigger endpoints.

TIPSC runs directly in-process.
DFV and Discovery remain Kafka-driven.

Endpoints:
    POST /sessions/{session_id}/trigger/tipsc
    POST /sessions/{session_id}/followup
    POST /sessions/{session_id}/trigger/dfv
    POST /sessions/{session_id}/trigger/discovery
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, Request, status
from pydantic import BaseModel
from core.constants import UserRole
from dependencies.auth import require_role
from kafka.producer import kafka_producer
from kafka.topics import KafkaTopic
from repositories.session_repo import session_repo
from schemas.auth import CurrentUser
from schemas.flow import (
    DFVTriggerRequest,
    DiscoveryTriggerRequest,
    FlowTriggerResponse,
    FollowupAnswerRequest,
)
from services.audit_service import audit_service
from services.flow_service import FlowService
from utils.object_id import validate_object_id
from utils.response import success_response


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/sessions",
    tags=["Flows"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Flow service dependency
# ─────────────────────────────────────────────────────────────────────────────


def _get_flow_service() -> FlowService:

    class KafkaAdaptor:

        async def publish(
            self,
            topic: str,
            payload: dict | BaseModel,
        ) -> str:

            from models.schema import (
                DFVJobMessage,
                DiscoveryJobMessage,
            )

            topic_to_model = {
                KafkaTopic.USER_SESSION_DFV: DFVJobMessage,
                KafkaTopic.USER_SESSION_DISCOVERY: DiscoveryJobMessage,
            }

            if isinstance(payload, BaseModel):
                validated_payload = payload
            else:
                model_cls = topic_to_model.get(topic)

                if model_cls is not None:
                    validated_payload = model_cls(**payload)
                else:
                    validated_payload = payload

            return await kafka_producer.publish(
                topic=topic,
                payload=validated_payload,
            )


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
        session_repo=session_repo,
        kafka_producer=KafkaAdaptor(),
        audit_service=AuditAdaptor(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# TIPSC
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/{session_id}/trigger/tipsc",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger TIPSC evaluation",
)
async def trigger_tipsc(
    request: Request,
    session_id: str,
    current_user: Annotated[
        CurrentUser,
        Depends(require_role(UserRole.STUDENT, UserRole.MENTOR_WORKSPACE)),
    ],
):

    validate_object_id(session_id)

    flow_service = _get_flow_service()

    result = await flow_service.trigger_tipsc(
        session_id=session_id,
        student_id=current_user.user_id if current_user.is_student else None,
        workspace_id=current_user.workspace_id,
    )

    return success_response(
        data=result,
        request=request,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TIPSC FOLLOW-UP
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/{session_id}/followup",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit TIPSC follow-up answer",
    description=(
        "Submits the founder answer for the session's pending TIPSC question "
        "and asynchronously resumes TIPSC re-evaluation."
    ),
)
async def submit_followup(
    request: Request,
    session_id: str,
    body: FollowupAnswerRequest,
    current_user: Annotated[
        CurrentUser,
        Depends(require_role(UserRole.STUDENT, UserRole.MENTOR_WORKSPACE)),
    ],
):

    validate_object_id(session_id)

    flow_service = _get_flow_service()

    result = await flow_service.submit_followup_answer(
        session_id=session_id,
        student_id=current_user.user_id if current_user.is_student else None,
        answer=body.answer,
        workspace_id=current_user.workspace_id,
    )

    return success_response(
        data=result,
        request=request,
    )


# ─────────────────────────────────────────────────────────────────────────────
# DFV
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/{session_id}/trigger/dfv",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger DFV evaluation",
)
async def trigger_dfv(
    request: Request,
    session_id: str,
    body: DFVTriggerRequest,
    current_user: Annotated[
        CurrentUser,
        Depends(require_role(UserRole.STUDENT, UserRole.MENTOR_WORKSPACE)),
    ],
    idempotency_key: Annotated[
        Optional[str],
        Header(alias="Idempotency-Key"),
    ] = None,
):

    validate_object_id(session_id)


    if idempotency_key:

        session = await session_repo.find_by_id(
            session_id
        )

        if (
            session
            and session.correlation_id
            and session.status.value == "dfv_waiting"
        ):

            return success_response(
                data={
                    "session_id": session_id,
                    "flow": "dfv",
                    "status": session.status.value,
                    "correlation_id": (
                        session.correlation_id
                    ),
                    "triggered_at": (
                        session.updated_at.isoformat()
                    ),
                },
                request=request,
            )


    flow_service = _get_flow_service()

    result = await flow_service.trigger_dfv(
        session_id=session_id,
        student_id=current_user.user_id if current_user.is_student else None,
        dfv_inputs=body.model_dump(),
        workspace_id=current_user.workspace_id,
    )

    return success_response(
        data=result,
        request=request,
    )


# ─────────────────────────────────────────────────────────────────────────────
# DISCOVERY
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/{session_id}/trigger/discovery",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Discovery evaluation",
)
async def trigger_discovery(
    request: Request,
    session_id: str,
    current_user: Annotated[
        CurrentUser,
        Depends(require_role(UserRole.STUDENT, UserRole.MENTOR_WORKSPACE)),
    ],
    body: DiscoveryTriggerRequest,
    idempotency_key: Annotated[
        Optional[str],
        Header(alias="Idempotency-Key"),
    ] = None,
):

    validate_object_id(session_id)


    if idempotency_key:

        session = await session_repo.find_by_id(
            session_id
        )

        if (
            session
            and session.correlation_id
            and session.status.value
            == "discovery_waiting"
        ):

            return success_response(
                data={
                    "session_id": session_id,
                    "flow": "discovery",
                    "status": session.status.value,
                    "correlation_id": (
                        session.correlation_id
                    ),
                    "triggered_at": (
                        session.updated_at.isoformat()
                    ),
                },
                request=request,
            )


    flow_service = _get_flow_service()

    result = await flow_service.trigger_discovery(
        session_id=session_id,
        student_id=current_user.user_id if current_user.is_student else None,
        discovery_inputs=body.model_dump(),
        workspace_id=current_user.workspace_id,
    )

    return success_response(
        data=result,
        request=request,
    )