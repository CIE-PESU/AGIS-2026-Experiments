# backend/app/api/internal/worker_updates.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from app.dependencies.worker_auth import verify_worker_secret
from app.schemas.worker import WorkerOutputRequest, WorkerFailureRequest
from app.services.worker_service import worker_service

# Apply the worker authentication dependency globally to this router
router = APIRouter(
    tags=["Internal Worker Tracking"],
    dependencies=[Depends(verify_worker_secret)]
)

@router.post("/sessions/{session_id}/output", status_code=status.HTTP_200_OK)
async def receive_worker_output(
    session_id: str,
    req: WorkerOutputRequest,
    background_tasks: BackgroundTasks,
):
    """
    Endpoint for AI workers to post successful flow outputs back to the core database.
    """
    return await worker_service.accept_flow_output(
        session_id=session_id,
        flow=req.flow,
        correlation_id=req.correlation_id,
        output=req.output,
        duration_seconds=req.duration_seconds,
        worker_id=req.worker_id,
        background_tasks=background_tasks,
    )


@router.post("/sessions/{session_id}/failure", status_code=status.HTTP_200_OK)
async def receive_worker_failure(
    session_id: str,
    req: WorkerFailureRequest,
    background_tasks: BackgroundTasks,
):
    """
    Endpoint for AI workers to flag a flow failure so the session can be updated.
    """
    return await worker_service.accept_flow_failure(
        session_id=session_id,
        flow=req.flow,
        correlation_id=req.correlation_id,
        error_code=req.error_code,
        error_message=req.error_message,
        retry_count=req.retry_count,
        background_tasks=background_tasks,
    )