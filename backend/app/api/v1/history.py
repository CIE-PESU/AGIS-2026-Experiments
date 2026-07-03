"""
api/v1/history.py — Session history endpoints.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.dependencies.auth import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.history import AuditLogResponse
from app.services.history_service import history_service
from app.utils.response import paginated_response

router = APIRouter(
    tags=["History"],
)


@router.get(
    "/sessions/{session_id}/history",
    status_code=status.HTTP_200_OK,
    summary="Get session history",
    description="Returns chronological audit history for a session.",
)
async def get_session_history(
    request: Request,
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    history = await history_service.get_session_history(
        session_id=session_id,
        current_user=current_user,
        page=page,
        limit=limit,
    )

    total = len(history)

    return paginated_response(
        data=[
            AuditLogResponse.model_validate(item).model_dump()
            for item in history
        ],
        request=request,
        page=page,
        limit=limit,
        total=total,
    )