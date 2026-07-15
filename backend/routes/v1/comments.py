"""
Comment endpoints:
  POST   /sessions/{id}/comments
  GET    /sessions/{id}/comments
  DELETE /comments/{comment_id}
"""

from fastapi import APIRouter, Depends, status

from dependencies.auth import CurrentUser, get_current_user
from repositories.comment_repo import comment_repo
from repositories.session_repo import session_repo
from schemas.comment import CommentCreateRequest, CommentListItem, CommentResponse
from services.audit_service import audit_service
from services.comment_service import CommentService

router = APIRouter(tags=["Comments"])


def get_comment_service() -> CommentService:
    """Wire the real singletons — comment_repo, session_repo, audit_service."""
    return CommentService(
        comment_repo=comment_repo,  # type: ignore[arg-type]
        session_repo=session_repo,  # type: ignore[arg-type]
        audit_service=audit_service,  # type: ignore[arg-type]
    )


@router.post(
    "/sessions/{session_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a mentor comment to a session",
    description="Mentor and Admin only. Creates a comment on the given session.",
)
async def add_comment(
    session_id: str,
    body: CommentCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service),
):
    return await comment_service.add_comment(session_id, current_user, body.comment)


@router.get(
    "/sessions/{session_id}/comments",
    response_model=list[CommentListItem],
    summary="List comments for a session",
    description="Returns all non-deleted comments for the session. RBAC enforced.",
)
async def get_comments(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service),
):
    return await comment_service.get_comments(session_id, current_user)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete (soft) a mentor comment",
    description="Mentor can delete their own comments. Admin can delete any comment.",
)
async def delete_comment(
    comment_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service),
):
    await comment_service.delete_comment(comment_id, current_user)
