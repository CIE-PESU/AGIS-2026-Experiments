"""
schemas/mentor.py — Pydantic request/response schemas for Mentor APIs.

Matches api-spec.md Section 7 exactly.

Endpoints:
  GET /mentor/sessions           → list[MentorSessionListItem]  (paginated)
  GET /mentor/sessions/{id}      → SessionResponse (full — imported from session.py)
  GET /mentor/teams              → list[MentorTeamResponse]
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────────────────────
# Session list item — summary shape for GET /mentor/sessions
# api-spec.md Section 7.1
# ─────────────────────────────────────────────────────────────────────────────

class MentorSessionListItem(BaseModel):
    """
    Summary session shape for the mentor's session list.

    Excludes full AI output for performance (list view optimization).
    Full detail is available via GET /mentor/sessions/{id}.

    Matches api-spec.md Section 7.1 response shape exactly:
      session_id, team_id, team_name, student_name, status,
      tipsc_score, ready_for_dfv, created_at, updated_at
    """

    session_id: str
    team_id: str
    team_name: Optional[str] = None       # resolved from teams collection in service
    student_name: Optional[str] = None    # resolved from users collection in service
    status: str
    tipsc_score: Optional[int] = None     # null until TIPSC completes
    ready_for_dfv: Optional[bool] = None  # null until TIPSC completes
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Team member info — embedded inside MentorTeamResponse
# ─────────────────────────────────────────────────────────────────────────────

class TeamMemberInfo(BaseModel):
    """Minimal user info embedded in team detail — api-spec.md Section 7.3."""

    user_id: str
    name: str
    srn: str


# ─────────────────────────────────────────────────────────────────────────────
# Team response — GET /mentor/teams
# api-spec.md Section 7.3
# ─────────────────────────────────────────────────────────────────────────────

class MentorTeamResponse(BaseModel):
    """
    Team detail returned by GET /mentor/teams.

    Matches api-spec.md Section 7.3 response shape exactly:
      team_id, team_name, member_count, active_session_count, members
    """

    team_id: str
    team_name: str
    member_count: int
    active_session_count: int = 0       # computed in service layer
    members: list[TeamMemberInfo] = []  # full member list with user details
