"""
api/v1/comments.py — Mentor comment API endpoints.

Endpoints:
  POST   /sessions/{session_id}/comments  → add_comment
  GET    /sessions/{session_id}/comments  → get_comments
  DELETE /comments/{comment_id}           → delete_comment

Access control:
  POST   — mentor, admin only
  GET    — student (own session), mentor (supervised teams), admin
  DELETE — mentor (own comment), admin
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from app.core.constants import UserRole
from app.dependencies.auth import get_current_user, require_role
from app.schemas.auth import CurrentUser
from app.schemas.comment import CommentCreateRequest, CommentListItem, CommentResponse
from app.services.comment_service import comment_service
from app.utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Comments"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /sessions/{session_id}/comments — Add a mentor comment
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/sessions/{session_id}/comments",
    status_code=status.HTTP_201_CREATED,
    summary="Add a mentor comment to a session",
    description=(
        "Allows a mentor or admin to leave feedback on a session. "
        "Mentors can only comment on sessions belonging to their supervised teams. "
        "Students cannot post comments (403)."
    ),
)
async def add_comment(
    request: Request,
    session_id: str,
    body: CommentCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.MENTOR, UserRole.ADMIN))],
):
    """
    POST /sessions/{session_id}/comments (mentor, admin only)

    Errors:
      403 INSUFFICIENT_PERMISSIONS — student calling this endpoint
      403 INSUFFICIENT_PERMISSIONS — mentor not assigned to this session's team
      404 SESSION_NOT_FOUND        — session does not exist
      422 VALIDATION_ERROR         — comment < 10 or > 2000 chars
    """
    comment = await comment_service.add_comment(
        session_id=session_id,
        comment_text=body.comment,
        current_user=current_user,
        background_tasks=background_tasks,
    )

    response_data = CommentResponse(
        comment_id=str(comment.id),
        session_id=comment.session_id,
        mentor_id=comment.mentor_id,
        mentor_name=comment.mentor_name,
        comment=comment.comment,
        created_at=comment.created_at,
    ).model_dump()

    return success_response(data=response_data, request=request)


# ─────────────────────────────────────────────────────────────────────────────
# GET /sessions/{session_id}/comments — List comments for a session
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sessions/{session_id}/comments",
    status_code=status.HTTP_200_OK,
    summary="List mentor comments for a session",
    description=(
        "Returns all non-deleted comments for the session. "
        "Students may only view comments on their own session. "
        "Soft-deleted comments are always excluded."
    ),
)
async def get_comments(
    request: Request,
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """
    GET /sessions/{session_id}/comments

    Role access:
      - student : own sessions only (404 if belongs to another student)
      - mentor  : sessions in their supervised teams
      - admin   : any session

    Errors:
      401 TOKEN_INVALID    — missing/invalid JWT
      404 SESSION_NOT_FOUND
    """
    comments = await comment_service.get_comments(
        session_id=session_id,
        current_user=current_user,
    )

    data = [
        CommentListItem(
            comment_id=str(c.id),
            mentor_name=c.mentor_name,
            comment=c.comment,
            created_at=c.created_at,
        ).model_dump()
        for c in comments
    ]

    return success_response(data=data, request=request)


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /comments/{comment_id} — Soft-delete a comment
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a mentor comment",
    description=(
        "Mentors can delete only their own comments. "
        "Admins can delete any comment. "
        "The comment is soft-deleted (not removed from DB — deleted=True)."
    ),
)
async def delete_comment(
    request: Request,
    comment_id: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.MENTOR, UserRole.ADMIN))],
):
    """
    DELETE /comments/{comment_id} (mentor, admin only)

    Errors:
      401 TOKEN_INVALID            — missing/invalid JWT
      403 INSUFFICIENT_PERMISSIONS — mentor trying to delete another mentor's comment
      404 COMMENT_NOT_FOUND        — comment not found or already deleted
    """
    await comment_service.delete_comment(
        comment_id=comment_id,
        current_user=current_user,
        background_tasks=background_tasks,
    )

    return success_response(
        data={"comment_id": comment_id, "deleted": True},
        request=request,
    )
