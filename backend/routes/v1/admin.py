# app/api/v1/admin.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query

import json
from pathlib import Path
from pydantic import BaseModel
from dependencies.auth import require_admin
from schemas.auth import CurrentUser
from services import admin_service
from core.security import cipher
from models.user import User

class MentorCreateRequest(BaseModel):
    name: str
    email: str
    password: str

# Apply the admin lock to every route in this file automatically
router = APIRouter(
    tags=["Admin"],
    dependencies=[Depends(require_admin())]
)

@router.post("/mentors")
async def create_mentor(req: MentorCreateRequest):
    """Admin: Create a new mentor with an encrypted password."""
    # Check if mentor already exists
    existing = await User.find_one(User.srn == req.email.upper())
    if existing:
        return {"error": "Mentor already exists"}
    
    enc_pw = cipher.encrypt(req.password.encode()).decode()
    new_mentor = User(
        srn=req.email.upper(),
        name=req.name,
        email=req.email,
        role="mentor",
        encrypted_password=enc_pw
    )
    await new_mentor.insert()
    
    # Also save to seed_data.json for git tracking
    seed_file = Path(__file__).resolve().parent.parent.parent / "scripts" / "seed_data.json"
    if seed_file.exists():
        try:
            with open(seed_file, "r") as f:
                data = json.load(f)
            
            data.append({
                "srn": req.email.upper(),
                "name": req.name,
                "email": req.email,
                "role": "mentor",
                "encrypted_password": enc_pw
            })
            
            with open(seed_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            # We don't want to fail the API request if file write fails, but we should log it
            print(f"Failed to write to seed_data.json: {e}")
            
    return {"message": "Mentor created successfully"}

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