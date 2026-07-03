# backend/app/api/internal/worker_updates.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies.worker_auth import verify_worker_secret

# Apply the worker authentication dependency globally to this router
router = APIRouter(
    tags=["Internal Worker Tracking"],
    dependencies=[Depends(verify_worker_secret)]
)

@router.post("/sessions/{session_id}/output")
async def receive_worker_output(session_id: str):
    """
    Endpoint for AI workers to post successful flow outputs back to the core database.
    """
    # Day 2 Skeleton: Return 501 until DB repositories are wired up
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Worker output parsing not yet implemented."
    )


@router.post("/sessions/{session_id}/failure")
async def receive_worker_failure(session_id: str):
    """
    Endpoint for AI workers to flag a flow failure so the session can be updated.
    """
    # Day 2 Skeleton: Return 501 until DB repositories are wired up
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Worker failure handling not yet implemented."
    )