"""
api/v1/mentor.py — Mentor API route handlers.

Endpoints:
  GET /mentor/sessions           → list_mentor_sessions (paginated, filterable)
  GET /mentor/sessions/{id}      → get_mentor_session_detail (full)
  GET /mentor/teams              → list_mentor_teams

Access control:
  All endpoints — Mentor role only.

Route handlers are thin — parse request, call service, wrap response.
No business logic or repo calls here.
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request

from core.constants import UserRole
from dependencies.auth import require_role
from exceptions.base import SessionNotFoundError
from schemas.auth import CurrentUser
from schemas.mentor import MentorSessionListItem, MentorTeamResponse
from services.mentor_service import mentor_service
from utils.response import paginated_response, success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mentor", tags=["Mentor"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /mentor/sessions — paginated session list for mentor
# api-spec.md Section 7.1
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sessions",
    summary="List sessions for mentor's supervised teams",
    description=(
        "Returns a paginated summary list of all sessions belonging to teams "
        "supervised by the authenticated mentor. Supports filtering by `status` "
        "and `team_id`. Mentor with no assigned teams returns an empty list."
    ),
)
async def list_mentor_sessions(
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.MENTOR))],
    team_id: Optional[str] = Query(
        default=None,
        description="Filter sessions by a specific team ID.",
    ),
    status: Optional[str] = Query(
        default=None,
        description="Filter sessions by status (e.g. tipsc_completed, dfv_running).",
    ),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)."),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page."),
) -> dict:
    """GET /mentor/sessions — list supervised sessions with optional filters."""

    filters: dict = {}
    if status:
        filters["status"] = status
    if team_id:
        filters["team_id"] = team_id

    items, total = await mentor_service.get_supervised_sessions(
        mentor_id=current_user.user_id,
        mentor_team_ids=current_user.mentor_team_ids,
        filters=filters or None,
        page=page,
        limit=limit,
    )

    serialized = [item.model_dump() for item in items]

    return paginated_response(
        data=serialized,
        request=request,
        page=page,
        limit=limit,
        total=total,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /mentor/sessions/{session_id} — full session detail for mentor
# api-spec.md Section 7.2
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sessions/{session_id}",
    summary="Get full session detail (mentor view)",
    description=(
        "Returns the full session document including all AI outputs (TIPSC, DFV, Discovery). "
        "The mentor must supervise the session's team — returns 404 otherwise."
    ),
)
async def get_mentor_session_detail(
    request: Request,
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.MENTOR))],
) -> dict:
    """GET /mentor/sessions/{session_id} — full detail, mentor-scoped."""

    session = await mentor_service.get_supervised_session_detail(
        session_id=session_id,
        mentor_team_ids=current_user.mentor_team_ids,
    )

    # Serialize the full session document
    session_data = session.model_dump(mode="json")
    session_data["session_id"] = str(session.id)
    session_data.pop("id", None)

    return success_response(data=session_data, request=request)


# ─────────────────────────────────────────────────────────────────────────────
# GET /mentor/teams — list all supervised teams with full member detail
# api-spec.md Section 7.3
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/teams",
    summary="List mentor's supervised teams",
    description=(
        "Returns the list of teams assigned to the authenticated mentor, "
        "including member details and active session counts."
    ),
)
async def list_mentor_teams(
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.MENTOR))],
) -> dict:
    """GET /mentor/teams — list teams supervised by this mentor."""

    teams = await mentor_service.get_mentor_teams(
        mentor_id=current_user.user_id,
        mentor_team_ids=current_user.mentor_team_ids,
    )

    serialized = [t.model_dump() for t in teams]

    return success_response(data=serialized, request=request)
