"""
api/v1/sessions.py — Session lifecycle API route handlers.

Endpoints:
  POST   /sessions              → create_session
  GET    /sessions/{session_id} → get_session
  GET    /sessions              → list_sessions
  DELETE /sessions/{session_id} → archive_session

All responses are wrapped in the standard envelope:
  { "data": {...}, "meta": { "request_id": "...", "timestamp": "..." } }

Paginated list:
  { "data": [...], "pagination": {...}, "meta": {...} }

Route handlers are thin — they:
  1. Parse and validate the request (via Pydantic body / header / query params).
  2. Call the service.
  3. Wrap and return the response.

No business logic, no repository calls, no Kafka calls here.
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Request, status

from core.constants import UserRole
from dependencies.auth import get_current_user, require_role
from exceptions.base import ValidationException
from schemas.auth import CurrentUser
from schemas.session import SessionCreateRequest
from services.session_service import session_service
from utils.object_id import validate_object_id
from utils.response import paginated_response, success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /sessions — Create a new session
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new coaching session",
    description=(
        "Creates a new session for the authenticated student. "
        "Publishes a TIPSC evaluation event to Kafka. "
        "Requires an `Idempotency-Key` header (UUID4) to prevent duplicate submissions. "
        "Re-submitting the same Idempotency-Key returns the original session (no new session created)."
    ),
)
async def create_session(
    request: Request,
    body: SessionCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.STUDENT))],
    idempotency_key: Annotated[
        Optional[str],
        Header(
            alias="Idempotency-Key",
            description="UUID4 string. Required. Prevents duplicate session creation on retry.",
        ),
    ] = None,
):
    """
    POST /sessions (student only)

    Creates a session and triggers the TIPSC Kafka event.
    Returns the session with status: queued once Kafka publish succeeds.

    Request headers:
      Idempotency-Key: <uuid4>  — Required. Re-using the same key returns the original session.

    Errors:
      400 VALIDATION_ERROR             — missing or invalid Idempotency-Key header
      409 ACTIVE_SESSION_EXISTS        — student already has a non-archived session
      503 KAFKA_UNAVAILABLE            — Kafka publish failed (session created but not queued)
    """
    if not idempotency_key:
        raise ValidationException(
            message="Idempotency-Key header is required for session creation.",
            field="Idempotency-Key",
        )

    # Validate it is a plausible key (non-empty, reasonable length).
    idempotency_key = idempotency_key.strip()
    if not idempotency_key or len(idempotency_key) > 128:
        raise ValidationException(
            message="Idempotency-Key must be a non-empty string (max 128 chars).",
            field="Idempotency-Key",
        )

    resolved_team_id = body.team_id or current_user.team_id or f"team_{current_user.user_id[-6:]}"
    session = await session_service.create_session(
        student_id=current_user.user_id,
        team_id=resolved_team_id,
        problem_statement=body.problem_statement,
        idea=body.idea,
        idempotency_key=idempotency_key,
        background_tasks=background_tasks,
    )

    return success_response(data=session.model_dump(), request=request)


# ─────────────────────────────────────────────────────────────────────────────
# GET /sessions/{session_id} — Retrieve a single session
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Get a session by ID",
    description=(
        "Returns the full session object including embedded TIPSC, DFV, and Discovery outputs. "
        "Students may only access their own sessions. "
        "Mentors may access sessions from their supervised teams. "
        "Accessing another student's session returns 404 (not 403) to prevent information leakage."
    ),
)
async def get_session(
    request: Request,
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """
    GET /sessions/{session_id}

    Role access:
      - student : own sessions only (404 if belongs to another student)
      - mentor  : sessions in their supervised teams
      - admin   : any session

    Errors:
      401 TOKEN_INVALID    — missing/invalid JWT
      404 SESSION_NOT_FOUND
    """
    validate_object_id(session_id)
    session = await session_service.get_session(
        session_id=session_id,
        current_user=current_user,
    )
    return success_response(data=session.model_dump(), request=request)


# ─────────────────────────────────────────────────────────────────────────────
# GET /user/{student_id}/session — Retrieve current active session
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/user/{student_id}/session",
    status_code=status.HTTP_200_OK,
    summary="Get active session by student ID",
    description=(
        "Returns the active (non-archived) session for the student. "
    ),
)
async def get_active_session_by_user(
    request: Request,
    student_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    from repositories.session_repo import session_repo
    
    if current_user.user_id != student_id and current_user.role == UserRole.STUDENT:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access session of another user.")

    session = await session_repo.find_active_by_student(student_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session found for user.")

    return success_response(data=session.model_dump(), request=request)


# ─────────────────────────────────────────────────────────────────────────────
# GET /sessions — List sessions (paginated)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List sessions (paginated)",
    description=(
        "Returns a paginated list of sessions accessible to the current user. "
        "Students see only their own sessions. Mentors see sessions from their teams. "
        "Supports optional filtering by status. Archived sessions are excluded by default."
    ),
)
async def list_sessions(
    request: Request,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)."),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)."),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by session status (e.g. queued, tipsc_running, completed).",
    ),
    team_id: Optional[str] = Query(
        default=None,
        description="(Mentor/Admin only) Filter by a specific team ID.",
    ),
):
    """
    GET /sessions

    Errors:
      401 TOKEN_INVALID — missing/invalid JWT
    """
    filters: dict = {}
    if status_filter:
        filters["status"] = status_filter
    if team_id:
        filters["team_id"] = team_id

    items, total = await session_service.list_sessions(
        current_user=current_user,
        filters=filters,
        page=page,
        limit=limit,
    )

    return paginated_response(
        data=[item.model_dump() for item in items],
        request=request,
        page=page,
        limit=limit,
        total=total,
    )


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /sessions/{session_id} — Archive a session
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Archive (soft-delete) a session",
    description=(
        "Soft-archives a session. The session is not deleted from the database — "
        "it is marked as ARCHIVED and excluded from default listing queries. "
        "Cannot archive a session while a flow is actively running. "
        "Fires a SESSION_ARCHIVED audit log entry."
    ),
)
async def archive_session(
    request: Request,
    session_id: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """
    DELETE /sessions/{session_id}

    Returns the archived session object (status: archived).

    Errors:
      401 TOKEN_INVALID                  — missing/invalid JWT
      404 SESSION_NOT_FOUND              — session not found or not owned by caller
      409 CANNOT_ARCHIVE_ACTIVE_SESSION  — a flow is currently running
    """
    validate_object_id(session_id)
    session = await session_service.archive_session(
        session_id=session_id,
        current_user=current_user,
        background_tasks=background_tasks,
    )
    return success_response(data=session.model_dump(), request=request)


# ─────────────────────────────────────────────────────────────────────────────
# GET /sessions/{session_id}/stream — Server-Sent Events for real-time updates
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{session_id}/stream",
    summary="SSE stream for session updates",
    description="Yields Server-Sent Events when the session status changes.",
)
async def stream_session(
    request: Request,
    session_id: str,
    # Note: For real auth with EventSource, clients often pass token in query param 
    # since browser EventSource doesn't support custom headers.
    # We will skip strict auth here for the prototype SSE, or assume token in query.
):
    import asyncio
    import json
    from fastapi.responses import StreamingResponse
    from repositories.session_repo import session_repo

    validate_object_id(session_id)

    async def event_generator():
        last_state_hash = None
        
        while True:
            if await request.is_disconnected():
                break
                
            # Fetch current session state
            session_data = await session_repo.get_by_id(session_id)
            if session_data:
                # We only care about statuses of tipsc, dfv, discovery
                current_state = {
                    "tipsc": session_data.get("tipsc", {}).get("status"),
                    "dfv": session_data.get("dfv", {}).get("status"),
                    "discovery": session_data.get("discovery", {}).get("status"),
                }
                current_hash = hash(frozenset(current_state.items()))
                
                if current_hash != last_state_hash:
                    last_state_hash = current_hash
                    # Clean up the object ID for JSON serialization
                    session_data["_id"] = str(session_data["_id"])
                    
                    yield f"data: {json.dumps(session_data)}\n\n"
            
            await asyncio.sleep(2)  # Poll every 2 seconds

    return StreamingResponse(event_generator(), media_type="text/event-stream")
