# app/api/v1/admin.py
import asyncio
from datetime import datetime
from functools import wraps
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pymongo.errors import DuplicateKeyError

from core.flow_results import completed_flow_output
from core.security import hash_password
from core.sync import dump_seed_data
from dependencies.auth import require_admin, require_mentor_or_admin
from models.session import Session
from models.team import Team
from models.user import User
from repositories.session_repo import session_repo
from schemas.auth import CurrentUser
from schemas.workspace import WorkspaceCreateRequest
from services import admin_service
from services.mentor_service import sync_mentor_teams
from services.workspace_service import workspace_service
from state_machine.states import SessionStatus
from utils.object_id import validate_object_id


def serialize_team_mutation(function):
    """Serialize membership edits in the supported single-API deployment."""

    @wraps(function)
    async def wrapped(*args, **kwargs):
        async with kwargs["request"].app.state.team_mutation_lock:
            return await function(*args, **kwargs)

    return wrapped


async def validate_team_references(req: "TeamCreateRequest", team_id: str | None = None) -> None:
    if req.mentor_id:
        validate_object_id(req.mentor_id, "mentor_id")
        mentor = await User.get(req.mentor_id)
        if mentor is None or mentor.role != "mentor":
            raise HTTPException(422, "mentor_id must identify a mentor")
    students = await User.find({"srn": {"$in": req.members}, "role": "student"}).to_list()
    if len(students) != len(req.members):
        raise HTTPException(422, "Every team member must identify an existing student SRN")
    if any(student.team_id and student.team_id != team_id for student in students):
        raise HTTPException(409, "A student is already assigned to another team")


async def sync_student_session_teams(student_srns: list[str], new_team_id: str | None):
    """Synchronize Session.team_id for active sessions when student team membership changes."""
    if not student_srns:
        return
    students = await User.find({"srn": {"$in": student_srns}}).to_list()
    student_ids = [str(s.id) for s in students]
    if student_ids:
        await Session.find(
            {"student_id": {"$in": student_ids}, "status": {"$ne": SessionStatus.ARCHIVED.value}}
        ).update({"$set": {"team_id": new_team_id or ""}})


class MentorCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    email: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class MentorUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    email: str | None = None


class TeamCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    mentor_id: str | None = None
    members: list[str] = Field(default_factory=list)

    @field_validator("members")
    @classmethod
    def normalized_members(cls, values: list[str]) -> list[str]:
        values = [value.strip().upper() for value in values]
        if any(not value for value in values) or len(values) != len(set(values)):
            raise ValueError("Team members must be distinct, nonblank student SRNs")
        return values


class TeamUpdateRequest(TeamCreateRequest):
    pass


# Remove the global admin lock so mentors can access read-only routes
router = APIRouter(tags=["Admin"])


@router.post("/mentors", dependencies=[Depends(require_admin())])
async def create_mentor(req: MentorCreateRequest, background_tasks: BackgroundTasks):
    """Admin: Create a new mentor without credentials."""
    import uuid

    clean_name = req.name.strip()
    email = (
        req.email.strip()
        if req.email and req.email.strip()
        else f"{clean_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@agis.local"
    )
    srn = email.upper()

    # Check if mentor already exists
    existing = await User.find_one(User.srn == srn)
    if existing:
        raise HTTPException(409, "Mentor already exists")

    enc_pw = await asyncio.to_thread(hash_password, req.password) if req.password else None
    new_mentor = User(srn=srn, name=clean_name, email=email, role="mentor", password_hash=enc_pw)
    try:
        await new_mentor.insert()
    except DuplicateKeyError as exc:
        raise HTTPException(409, "Mentor already exists") from exc

    background_tasks.add_task(dump_seed_data)

    return {
        "message": "Mentor created successfully",
        "data": {"id": str(new_mentor.id), "name": new_mentor.name},
    }


@router.get("/mentors", dependencies=[Depends(require_mentor_or_admin())])
async def list_mentors():
    """Admin: List all mentors."""
    mentors = await User.find(User.role == "mentor").to_list()
    data = []
    for m in mentors:
        m_dict = m.model_dump()
        m_dict["id"] = str(m.id)
        m_dict.pop("encrypted_password", None)
        m_dict.pop("password_hash", None)
        data.append(m_dict)
    return {"data": data}


@router.put("/mentors/{mentor_id}", dependencies=[Depends(require_admin())])
async def update_mentor(
    mentor_id: str, req: MentorUpdateRequest, background_tasks: BackgroundTasks
):
    validate_object_id(mentor_id, "mentor_id")
    mentor = await User.get(mentor_id)
    if not mentor or mentor.role != "mentor":
        raise HTTPException(404, "Mentor not found")
    mentor.name = req.name.strip()
    if req.email and req.email.strip():
        mentor.email = req.email.strip()
        mentor.srn = mentor.email.upper()
    try:
        await mentor.save()
    except DuplicateKeyError as exc:
        raise HTTPException(409, "That email already belongs to another user") from exc
    background_tasks.add_task(dump_seed_data)
    return {"message": "Mentor updated successfully"}


@router.delete("/mentors/{mentor_id}", dependencies=[Depends(require_admin())])
@serialize_team_mutation
async def delete_mentor(mentor_id: str, background_tasks: BackgroundTasks, request: Request):
    validate_object_id(mentor_id, "mentor_id")
    mentor = await User.get(mentor_id)
    if not mentor or mentor.role != "mentor":
        raise HTTPException(404, "Mentor not found")
    from models.refresh_token import RefreshToken
    from repositories.workspace_repo import workspace_repo

    for workspace in await workspace_repo.find_active_workspaces(mentor_id=mentor_id):
        await workspace_service.revoke_workspace(workspace.workspace_id, background_tasks)
    await Team.find({"mentor_id": {"$in": [mentor_id, mentor.srn]}}).update(
        {"$set": {"mentor_id": ""}}
    )
    await RefreshToken.find({"user_id": mentor_id}).update({"$set": {"revoked": True}})
    await mentor.delete()
    background_tasks.add_task(dump_seed_data)
    return {"message": "Mentor deleted"}


@router.get("/students", dependencies=[Depends(require_mentor_or_admin())])
async def list_students(current_user: Annotated[CurrentUser, Depends(require_mentor_or_admin())]):
    """Admin: List all students."""
    query: dict = {"role": "student"}
    if current_user.is_mentor:
        query["team_id"] = {"$in": current_user.mentor_team_ids}
    students = await User.find(query).to_list()
    data = []
    for s in students:
        s_dict = s.model_dump()
        s_dict["id"] = str(s.id)
        s_dict.pop("encrypted_password", None)
        s_dict.pop("password_hash", None)

        # Attach real active session data
        active_session = await session_repo.find_active_by_student(str(s.id))
        if active_session:
            s_dict["session_id"] = str(active_session.id)
            s_dict["status"] = active_session.status
            s_dict["last_active"] = active_session.updated_at.isoformat()
            s_dict["discovery_completed"] = bool(completed_flow_output(active_session.discovery))
            if active_session.tipsc:
                s_dict["tips"] = active_session.tipsc.tips_rag_scores.model_dump()
                s_dict["tipsc"] = {"ready_for_dfv": active_session.tipsc.ready_for_dfv}
            else:
                s_dict["tips"] = {}
            if active_session.dfv:
                output = active_session.dfv.output or {}
                s_dict["dfv"] = (
                    output.get("decision")
                    or output.get("final_decision", {}).get("status")
                    or active_session.dfv.status
                )
                s_dict["dfv_raw"] = {"output": output}
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
async def list_teams(current_user: Annotated[CurrentUser, Depends(require_mentor_or_admin())]):
    """Admin: List all teams."""
    teams = await Team.find(
        {"mentor_id": current_user.user_id} if current_user.is_mentor else {}
    ).to_list()
    data = []
    for t in teams:
        t_dict = t.model_dump()
        t_dict["id"] = str(t.id)
        data.append(t_dict)
    return {"data": data}


@router.post("/teams", dependencies=[Depends(require_admin())])
@serialize_team_mutation
async def create_team(req: TeamCreateRequest, background_tasks: BackgroundTasks, request: Request):
    """Admin: Create a new team and update student references."""
    await validate_team_references(req)
    team = Team(team_name=req.name, mentor_id=req.mentor_id or "", members=req.members)
    await team.insert()
    # Update students' team_id and their active sessions
    if req.members:
        await User.find({"srn": {"$in": req.members}}).update({"$set": {"team_id": str(team.id)}})
        await sync_student_session_teams(req.members, str(team.id))
    if req.mentor_id:
        await sync_mentor_teams(req.mentor_id)
    background_tasks.add_task(dump_seed_data)
    return {"message": "Team created", "team": team.model_dump(mode="json")}


@router.put("/teams/{team_id}", dependencies=[Depends(require_admin())])
@serialize_team_mutation
async def update_team(
    team_id: str, req: TeamUpdateRequest, background_tasks: BackgroundTasks, request: Request
):
    """Admin: Update an existing team."""
    validate_object_id(team_id, "team_id")
    team = await Team.get(team_id)
    if not team:
        raise HTTPException(404, "Team not found")
    await validate_team_references(req, team_id)

    old_mentor_id = team.mentor_id
    old_members = team.members or []

    # Clear old members' team_id and sessions
    if old_members:
        removed = [srn for srn in old_members if srn not in req.members]
        await User.find({"srn": {"$in": removed}, "team_id": team_id}).update(
            {"$set": {"team_id": None}}
        )
        await sync_student_session_teams(removed, None)

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
@serialize_team_mutation
async def delete_team(team_id: str, background_tasks: BackgroundTasks, request: Request):
    validate_object_id(team_id, "team_id")
    team = await Team.get(team_id)
    if not team:
        raise HTTPException(404, "Team not found")

    old_mentor_id = team.mentor_id
    if team.members:
        await User.find({"srn": {"$in": team.members}, "team_id": team_id}).update(
            {"$set": {"team_id": None}}
        )
        await sync_student_session_teams(team.members, None)

    await team.delete()
    if old_mentor_id:
        await sync_mentor_teams(old_mentor_id)

    background_tasks.add_task(dump_seed_data)
    return {"message": "Team deleted"}


@router.get("/sessions", dependencies=[Depends(require_admin())])
async def list_all_sessions(
    status: str | None = None,
    team_id: str | None = None,
    student_id: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Admin: List all sessions across the platform."""
    filters = {"status": status, "team_id": team_id, "student_id": student_id}
    # Clean out None values
    filters = {k: v for k, v in filters.items() if v is not None}

    sessions = await admin_service.get_all_sessions(filters, page, limit)
    return {"data": sessions, "pagination": {"page": page, "limit": limit}}


@router.get("/audit", dependencies=[Depends(require_admin())])
async def get_system_audit_log(
    event: str | None = None,
    actor: str | None = None,
    session_id: str | None = None,
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    """Admin: View system-wide audit logs."""
    filters = {
        "event": event,
        "actor": actor,
        "session_id": session_id,
        "from_date": from_date,
        "to_date": to_date,
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    logs = await admin_service.get_audit_log(filters, page, limit)
    return {"data": logs, "pagination": {"page": page, "limit": limit}}


@router.get("/metrics", dependencies=[Depends(require_admin())])
async def get_platform_metrics():
    """Admin: Get high-level platform health and usage metrics."""
    metrics = await admin_service.get_metrics()
    return {"data": metrics}


# ─────────────────────────────────────────────────────────────────────────────
# Workspace Link Management (Admin Only)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/workspaces")
async def create_workspace_magic_link(
    req: WorkspaceCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin())],
):
    """Admin: Create a new 1:1 Isolated Mentor Workspace magic link."""

    raw_token, resp = await workspace_service.create_magic_link_workspace(
        name=req.name,
        admin_id=current_user.user_id,
        mentor_id=req.mentor_id,
    )
    return {"data": resp.model_dump(), "meta": {"raw_token": raw_token}}


@router.get("/workspaces")
async def list_workspaces(
    current_user: Annotated[CurrentUser, Depends(require_admin())],
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """Admin: List created workspaces."""
    items, total = await workspace_service.list_workspaces(page=page, limit=limit)
    serialized = [item.model_dump() for item in items]
    return {"data": serialized, "pagination": {"page": page, "limit": limit, "total": total}}


@router.delete("/workspaces/{workspace_id}")
async def revoke_workspace(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUser, Depends(require_admin())],
):
    """Admin: Revoke a workspace and purge application data."""
    resp = await workspace_service.revoke_workspace(
        workspace_id=workspace_id,
        background_tasks=background_tasks,
    )
    return {"data": resp.model_dump()}
