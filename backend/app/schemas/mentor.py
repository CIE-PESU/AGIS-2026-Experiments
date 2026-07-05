"""
schemas/mentor.py — Pydantic request/response schemas for Mentor APIs.

Matches api-spec.md Section 7 exactly.

Endpoints:
  GET /mentor/sessions           → list[MentorSessionListItem]
  GET /mentor/sessions/{id}      → SessionResponse (full — imported from session.py)
  GET /mentor/teams              → list[MentorTeamResponse]
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MentorSessionListItem(BaseModel):
    """
    Summary session shape for the mentor's session list.
    Excludes full AI output for performance (list view optimization).
    Full detail is available via GET /mentor/sessions/{id}.
    """

    session_id: str
    student_id: str
    team_id: str
    problem_statement: str
    status: str
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

    # Simplified presence flags instead of full output objects
    has_tipsc: bool = False
    has_dfv: bool = False
    has_discovery: bool = False


class MentorTeamResponse(BaseModel):
    """
    Team summary returned by GET /mentor/teams.
    """

    team_id: str
    team_name: str
    mentor_id: str
    member_count: int
    created_at: Optional[datetime] = None
