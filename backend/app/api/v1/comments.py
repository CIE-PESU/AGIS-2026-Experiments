"""
Comment endpoints:
  POST   /sessions/{id}/comments
  GET    /sessions/{id}/comments
  DELETE /comments/{comment_id}

Same wiring caveat as api/v1/flows.py (B-12): this imports Palash's auth
deps and needs real comment_repo / session_repo / audit_service instances
plugged into get_comment_service(). comment_service.py itself has no such
dependency and is unit-tested standalone (tests/test_comment_service.py).
"""

from fastapi import APIRouter, Depends, status

from app.dependencies.auth import CurrentUser, get_current_user
from app.schemas.comment import CommentCreateRequest, CommentListItem, CommentResponse
from app.services.comment_service import CommentService

router = APIRouter(tags=["Comments"])


def get_comment_service() -> CommentService:
    """
    TODO: replace with real singletons once B-11 (comment_repo), B-04
    (session_repo), and B-08 (audit_service) are on develop-backend.
    """
    raise NotImplementedError(
        "Wire real comment_repo / session_repo / audit_service here "
        "once B-11 / B-04 / B-08 are merged."
    )


@router.post(
    "/sessions/{session_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
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
)
async def delete_comment(
    comment_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service),
):
    await comment_service.delete_comment(comment_id, current_user)
