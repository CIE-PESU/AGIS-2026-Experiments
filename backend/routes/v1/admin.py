# app/api/v1/admin.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, BackgroundTasks

import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, List
from dependencies.auth import require_admin, require_mentor_or_admin
from schemas.auth import CurrentUser
from services import admin_service
from core.security import cipher
from core.sync import dump_seed_data
from repositories.session_repo import session_repo
from models.user import User
from models.team import Team
from models.session import Session
from state_machine.states import SessionStatus
from services.mentor_service import sync_mentor_teams

async def sync_student_session_teams(student_srns: list[str], new_team_id: str | None):
    """Synchronize Session.team_id for active sessions when student team membership changes."""
    if not student_srns:
        return
    students = await User.find({"srn": {"$in": student_srns}}).to_list()
    student_ids = [str(s.id) for s in students]
    if student_ids:
        await Session.find({
            "student_id": {"$in": student_ids},
            "status": {"$ne": SessionStatus.ARCHIVED.value}
        }).update({"$set": {"team_id": new_team_id or ""}})

class MentorCreateRequest(BaseModel):
    name: str
    email: str
    password: str

class MentorUpdateRequest(BaseModel):
    name: str
    email: str

class TeamCreateRequest(BaseModel):
    name: str
    mentor_id: Optional[str] = None
    members: List[str] = []

class TeamUpdateRequest(BaseModel):
    name: str
    mentor_id: Optional[str] = None
    members: List[str] = []

# Remove the global admin lock so mentors can access read-only routes
router = APIRouter(
    tags=["Admin"]
)

@router.post("/mentors", dependencies=[Depends(require_admin())])
async def create_mentor(req: MentorCreateRequest, background_tasks: BackgroundTasks):
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
    
    background_tasks.add_task(dump_seed_data)
            
    return {"message": "Mentor created successfully"}

@router.get("/mentors", dependencies=[Depends(require_mentor_or_admin())])
async def list_mentors():
    """Admin: List all mentors."""
    mentors = await User.find(User.role == "mentor").to_list()
    data = []
    for m in mentors:
        m_dict = m.model_dump()
        m_dict["id"] = str(m.id)
        m_dict["encrypted_password"] = None
        data.append(m_dict)
    return {"data": data}

@router.put("/mentors/{mentor_id}", dependencies=[Depends(require_admin())])
async def update_mentor(mentor_id: str, req: MentorUpdateRequest, background_tasks: BackgroundTasks):
    mentor = await User.get(mentor_id)
    if not mentor:
        return {"error": "Mentor not found"}
    mentor.name = req.name
    mentor.email = req.email
    mentor.srn = req.email.upper()
    await mentor.save()
    background_tasks.add_task(dump_seed_data)
    return {"message": "Mentor updated successfully"}

@router.delete("/mentors/{mentor_id}", dependencies=[Depends(require_admin())])
async def delete_mentor(mentor_id: str, background_tasks: BackgroundTasks):
    mentor = await User.get(mentor_id)
    if not mentor:
        return {"error": "Mentor not found"}
    await mentor.delete()
    background_tasks.add_task(dump_seed_data)
    return {"message": "Mentor deleted"}

@router.get("/students", dependencies=[Depends(require_mentor_or_admin())])
async def list_students():
    """Admin: List all students."""
    students = await User.find(User.role == "student").to_list()
    data = []
    for s in students:
        s_dict = s.model_dump()
        s_dict["id"] = str(s.id)
        s_dict["encrypted_password"] = None
        
        # Attach real active session data
        active_session = await session_repo.find_active_by_student(str(s.id))
        if active_session:
            s_dict["session_id"] = str(active_session.id)
            s_dict["status"] = active_session.status
            if active_session.tipsc:
                s_dict["tips"] = active_session.tipsc.tips_rag_scores.model_dump()
            else:
                s_dict["tips"] = {}
            if active_session.dfv:
                s_dict["dfv"] = active_session.dfv.status
            else:
                s_dict["dfv"] = "Pending"
        else:
            s_dict["session_id"] = None
            s_dict["status"] = None
            s_dict["tips"] = {}
            s_dict["dfv"] = "Pending"
            
        data.append(s_dict)
    return {"data": data}

@router.get("/teams", dependencies=[Depends(require_mentor_or_admin())])
async def list_teams():
    """Admin: List all teams."""
    teams = await Team.find_all().to_list()
    data = []
    for t in teams:
        t_dict = t.model_dump()
        t_dict["id"] = str(t.id)
        data.append(t_dict)
    return {"data": data}

@router.post("/teams", dependencies=[Depends(require_admin())])
async def create_team(req: TeamCreateRequest, background_tasks: BackgroundTasks):
    """Admin: Create a new team and update student references."""
    team = Team(team_name=req.name, mentor_id=req.mentor_id or "", members=req.members)
    await team.insert()
    # Update students' team_id and their active sessions
    if req.members:
        await User.find({"srn": {"$in": req.members}}).update({"$set": {"team_id": str(team.id)}})
        await sync_student_session_teams(req.members, str(team.id))
    if req.mentor_id:
        await sync_mentor_teams(req.mentor_id)
    background_tasks.add_task(dump_seed_data)
    return {"message": "Team created", "team": team.model_dump()}

@router.put("/teams/{team_id}", dependencies=[Depends(require_admin())])
async def update_team(team_id: str, req: TeamUpdateRequest, background_tasks: BackgroundTasks):
    """Admin: Update an existing team."""
    team = await Team.get(team_id)
    if not team:
        return {"error": "Team not found"}
    
    old_mentor_id = team.mentor_id
    old_members = team.members or []
    
    # Clear old members' team_id and sessions
    if old_members:
        await User.find({"srn": {"$in": old_members}}).update({"$set": {"team_id": None}})
        await sync_student_session_teams(old_members, None)
    
    team.team_name = req.name
    team.mentor_id = req.mentor_id or ""
    team.members = req.members
    await team.save()
    
    # Set new members' team_id and sessions
    if req.members:
        await User.find({"srn": {"$in": req.members}}).update({"$set": {"team_id": str(team.id)}})
        await sync_student_session_teams(req.members, str(team.id))
    
    if old_mentor_id and old_mentor_id != req.mentor_id:
        await sync_mentor_teams(old_mentor_id)
    if req.mentor_id:
        await sync_mentor_teams(req.mentor_id)
    
    background_tasks.add_task(dump_seed_data)
    return {"message": "Team updated"}

@router.delete("/teams/{team_id}", dependencies=[Depends(require_admin())])
async def delete_team(team_id: str, background_tasks: BackgroundTasks):
    team = await Team.get(team_id)
    if not team:
        return {"error": "Team not found"}
    
    old_mentor_id = team.mentor_id
    if team.members:
        await User.find({"srn": {"$in": team.members}}).update({"$set": {"team_id": None}})
        await sync_student_session_teams(team.members, None)
        
    await team.delete()
    if old_mentor_id:
        await sync_mentor_teams(old_mentor_id)
    
    background_tasks.add_task(dump_seed_data)
    return {"message": "Team deleted"}



@router.get("/sessions", dependencies=[Depends(require_admin())])
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

@router.get("/audit", dependencies=[Depends(require_admin())])
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

@router.get("/metrics", dependencies=[Depends(require_admin())])
async def get_platform_metrics():
    """Admin: Get high-level platform health and usage metrics."""
    metrics = await admin_service.get_metrics()
    return {"data": metrics}