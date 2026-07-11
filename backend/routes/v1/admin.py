# app/api/v1/admin.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query

from dependencies.auth import require_admin
from schemas.auth import CurrentUser
from services import admin_service

# Apply the admin lock to every route in this file automatically
router = APIRouter(
    tags=["Admin"],
    dependencies=[Depends(require_admin())]
)

@router.get("/sessions")
async def list_all_sessions(
    status: Optional[str] = None,
    team_id: Optional[str] = None,
    student_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100)
):
    """Admin: List all sessions across the platform."""
    filters = {"status": status, "team_id": team_id, "student_id": student_id}
    # Clean out None values
    filters = {k: v for k, v in filters.items() if v is not None}
    
    sessions = await admin_service.get_all_sessions(filters, page, limit)
    return {"data": sessions, "pagination": {"page": page, "limit": limit}}

@router.get("/audit")
async def get_system_audit_log(
    event: Optional[str] = None,
    actor: Optional[str] = None,
    session_id: Optional[str] = None,
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=200)
):
    """Admin: View system-wide audit logs."""
    filters = {
        "event": event, "actor": actor, "session_id": session_id,
        "from_date": from_date, "to_date": to_date
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    
    logs = await admin_service.get_audit_log(filters, page, limit)
    return {"data": logs, "pagination": {"page": page, "limit": limit}}

@router.get("/metrics")
async def get_platform_metrics():
    """Admin: Get high-level platform health and usage metrics."""
    metrics = await admin_service.get_metrics()
    return {"data": metrics}