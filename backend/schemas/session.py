"""
schemas/session.py — Pydantic request/response schemas for the Sessions API.

Matches api-spec.md Section 3.2 exactly.

These schemas are used by:
  - api/v1/sessions.py  (route handlers — request body + response type hints)
  - services/session_service.py  (return types)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Embedded output sub-schemas (mirrors models/session.py embedded docs)
# These are used in SessionResponse so the full shape is returned to clients.
# ─────────────────────────────────────────────────────────────────────────────

class TIPSCScoreSchema(BaseModel):
    timing: int
    idea: int
    problem: int
    solution: int
    competition: int


class TIPSCOutputSchema(BaseModel):
    score: TIPSCScoreSchema
    total_score: int
    ready_for_dfv: bool
    compliance_flag: bool
    compliance_issues: list[str] = Field(default_factory=list)
    followups_asked: int = 0
    reasoning: str
    completed_at: datetime


class DFVDimensionSchema(BaseModel):
    score: int
    report: str
    recommendations: list[str] = Field(default_factory=list)


class DFVOutputSchema(BaseModel):
    desirability: DFVDimensionSchema
    feasibility: DFVDimensionSchema
    viability: DFVDimensionSchema
    overall_decision: str
    summary: str
    json_report: dict[str, Any] = Field(default_factory=dict)
    completed_at: datetime


class JTBDElementSchema(BaseModel):
    job: str
    outcome: str
    pain: str


class InterviewPlanSchema(BaseModel):
    target_segment: str
    interview_questions: list[str] = Field(default_factory=list)
    hypothesis_to_validate: str


class DiscoveryOutputSchema(BaseModel):
    jtbd_elements: list[JTBDElementSchema] = Field(default_factory=list)
    interview_plan: InterviewPlanSchema
    completed_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Request Schemas
# ─────────────────────────────────────────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    """
    POST /sessions request body.

    The client must also supply an `Idempotency-Key` header (UUID4).
    The route handler reads that from the request headers and passes it
    to session_service.create_session().
    """

    problem_statement: str = Field(
        ...,
        min_length=50,
        max_length=5000,
        description="Clear description of the problem the student's idea addresses (50–5000 chars).",
    )
    idea: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="The business idea or proposed solution.",
    )
    team_id: Optional[str] = Field(default=None, description="Override the JWT team_id if student is registering a new team")

    @field_validator("problem_statement", "idea", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return str(v).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Response Schemas
# ─────────────────────────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    """
    Full session shape returned by GET /sessions/{id}, POST /sessions, DELETE /sessions/{id}.

    Matches api-spec.md Section 3.2 SessionObject shape exactly.
    """

    session_id: str = Field(description="MongoDB ObjectId as string.")
    student_id: str
    team_id: str
    problem_statement: str
    idea: str
    status: str = Field(description="Current session state (see SessionStatus enum).")
    version: int = Field(description="Optimistic concurrency version counter.")

    # Embedded AI outputs — null until the corresponding flow completes.
    tipsc: Optional[TIPSCOutputSchema] = None
    dfv: Optional[DFVOutputSchema] = None
    discovery: Optional[DiscoveryOutputSchema] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

    # Correlation ID of the most recent Kafka event
    correlation_id: Optional[str] = None

    @classmethod
    def from_document(cls, session: Any) -> "SessionResponse":
        """
        Build a SessionResponse from a Session Beanie document.

        This helper avoids scattering `.model_dump()` calls across routes
        and provides a single place to translate MongoDB `id` → `session_id`.
        """
        return cls(
            session_id=str(session.id),
            student_id=session.student_id,
            team_id=session.team_id,
            problem_statement=session.problem_statement,
            idea=session.idea,
            status=session.status.value if hasattr(session.status, "value") else session.status,
            version=session.version,
            tipsc=session.tipsc.model_dump() if session.tipsc else None,
            dfv=session.dfv.model_dump() if session.dfv else None,
            discovery=session.discovery.model_dump() if session.discovery else None,
            created_at=session.created_at,
            updated_at=session.updated_at,
            archived_at=session.archived_at,
            correlation_id=session.correlation_id,
        )


class SessionListResponse(BaseModel):
    """
    Paginated list item returned inside the `data` array of GET /sessions.

    Contains the full session shape — clients can pre-populate detail views
    from the list response without an additional round-trip.
    """

    session_id: str
    student_id: str
    team_id: str
    problem_statement: str
    idea: str
    status: str
    version: int
    tipsc: Optional[TIPSCOutputSchema] = None
    dfv: Optional[DFVOutputSchema] = None
    discovery: Optional[DiscoveryOutputSchema] = None
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    correlation_id: Optional[str] = None

    @classmethod
    def from_document(cls, session: Any) -> "SessionListResponse":
        return cls(
            session_id=str(session.id),
            student_id=session.student_id,
            team_id=session.team_id,
            problem_statement=session.problem_statement,
            idea=session.idea,
            status=session.status.value if hasattr(session.status, "value") else session.status,
            version=session.version,
            tipsc=session.tipsc.model_dump() if session.tipsc else None,
            dfv=session.dfv.model_dump() if session.dfv else None,
            discovery=session.discovery.model_dump() if session.discovery else None,
            created_at=session.created_at,
            updated_at=session.updated_at,
            archived_at=session.archived_at,
            correlation_id=session.correlation_id,
        )
