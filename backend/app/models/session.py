"""
Session Beanie ODM model — `sessions` collection.
Core collection. Embeds TIPSC, DFV, and Discovery outputs.
"""

from datetime import datetime
from typing import Optional, Any
from beanie import Document
from pydantic import BaseModel, Field

from app.state_machine.states import SessionStatus


# ── Embedded output models ────────────────────────────────────────────────────

class TIPSCScore(BaseModel):
    timing: int
    idea: int
    problem: int
    solution: int
    competition: int


class TIPSCOutput(BaseModel):
    score: TIPSCScore
    total_score: int
    ready_for_dfv: bool
    compliance_flag: bool
    compliance_issues: list[str] = Field(default_factory=list)
    followups_asked: int = 0
    reasoning: str
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class DFVDimension(BaseModel):
    score: int
    report: str
    recommendations: list[str] = Field(default_factory=list)


class DFVOutput(BaseModel):
    desirability: DFVDimension
    feasibility: DFVDimension
    viability: DFVDimension
    overall_decision: str   # "GO" | "NO_GO" | "CONDITIONAL"
    summary: str
    json_report: dict[str, Any] = Field(default_factory=dict)
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class JTBDElement(BaseModel):
    job: str
    outcome: str
    pain: str


class InterviewPlan(BaseModel):
    target_segment: str
    interview_questions: list[str] = Field(default_factory=list)
    hypothesis_to_validate: str


class DiscoveryOutput(BaseModel):
    jtbd_elements: list[JTBDElement] = Field(default_factory=list)
    interview_plan: InterviewPlan
    completed_at: datetime = Field(default_factory=datetime.utcnow)


# ── DFV inputs (stored when student triggers DFV) ─────────────────────────────

class DFVInputs(BaseModel):
    desirability_context: str
    feasibility_context: str
    viability_context: str


# ── Session document ──────────────────────────────────────────────────────────

class Session(Document):
    team_id: str
    student_id: str
    problem_statement: str
    idea: str
    status: SessionStatus = SessionStatus.CREATED

    # Optimistic concurrency — incremented on every status change
    version: int = 0

    # Embedded outputs (null until the corresponding flow completes)
    tipsc: Optional[TIPSCOutput] = None
    dfv: Optional[DFVOutput] = None
    discovery: Optional[DiscoveryOutput] = None

    # Stored when student triggers DFV so the worker has the context
    dfv_inputs: Optional[DFVInputs] = None

    # Correlation ID of the most recent Kafka event (used by workers to validate)
    correlation_id: Optional[str] = None

    # Idempotency key for session creation (stored so duplicate POSTs are caught)
    idempotency_key: Optional[str] = None

    archived_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "sessions"
