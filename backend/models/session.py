"""
Session Beanie ODM model — `sessions` collection.
Core collection. Embeds TIPSC, DFV, and Discovery outputs.
"""

from datetime import datetime, timezone
from typing import Optional, Any
from beanie import Document
from pydantic import BaseModel, Field

from state_machine.states import SessionStatus


# ── Embedded output models ────────────────────────────────────────────────────

class TIPSCRAGScores(BaseModel):
    """RAG (Red/Amber/Green) scores for each TIPS dimension."""
    T: str = ""   # "GREEN" | "YELLOW" | "RED"
    I: str = ""
    P: str = ""
    S: str = ""
    T_reason: str = ""
    I_reason: str = ""
    P_reason: str = ""
    S_reason: str = ""


class TIPSCRefinedIdea(BaseModel):
    customer_segment:   str = ""
    qualified_problem:  str = ""
    consequence:        str = ""
    proposed_solution:  str = ""


class TIPSCOutput(BaseModel):
    """
    Shape produced by TIPSC-Agent/src/engine/async_pipeline_executor.py.
    MUST match TIPSC-Agent/src/models.py:TIPSCOutput field-for-field.
    """
    tips_rag_scores:     TIPSCRAGScores = TIPSCRAGScores()
    refined_idea:        TIPSCRefinedIdea = TIPSCRefinedIdea()
    solution_alignment:  str = ""   # "GREEN" | "YELLOW" | "RED"
    overall_readiness:   str = ""   # "STRONG" | "MODERATE" | "WEAK"
    ready_for_dfv:       bool = False
    needs_followup:      bool = False
    missing_criteria:    list[str] = Field(default_factory=list)
    compliance_flag:     bool = False
    reasoning:           str = ""   # populated from ethics/compliance context
    followups_asked:     int = 0
    completed_at:        datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DFVOutput(BaseModel):
    """
    Shape written by combined_agent_worker.py to the session's `dfv` field.
    The `output` sub-field contains the raw CrewAI crew output parsed from JSON.
    """
    correlation_id: str = ""
    status:         str = ""   # FlowStatus value: "done" | "failed" | "running" | "timeout"
    output:         Optional[dict[str, Any]] = None   # raw agent output dict
    error:          Optional[str] = None
    retry_count:    int = 0
    started_at:     Optional[datetime] = None
    completed_at:   Optional[datetime] = None
    idea_name:      str = ""


class DiscoveryOutput(BaseModel):
    """
    Shape written by combined_agent_worker.py to the session's `discovery` field.
    """
    correlation_id: str = ""
    status:         str = ""
    output:         Optional[dict[str, Any]] = None
    error:          Optional[str] = None
    retry_count:    int = 0
    started_at:     Optional[datetime] = None
    completed_at:   Optional[datetime] = None


# ── DFV inputs (stored when student triggers DFV) ─────────────────────────────

class DFVInputs(BaseModel):
    desirability_context: str
    feasibility_context: str
    viability_context: str


# ── Worker Failure Metadata ───────────────────────────────────────────────────

class WorkerFailureMetadata(BaseModel):
    flow: str
    error_code: str
    error_message: str
    retry_count: int = 0
    failed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── State transition audit trail ───────────────────────────────────────────────

class StateTransition(BaseModel):
    """Records a single status transition for audit purposes."""
    from_status: str
    to_status: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str = "system"   # "student" | "worker" | "system"
    trigger: str = ""       # e.g. "session_created", "tipsc_completed", "update_status"


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

    # Populated if a worker fails to process the flow
    failure_metadata: Optional[WorkerFailureMetadata] = None

    # Idempotency key for session creation (stored so duplicate POSTs are caught)
    idempotency_key: Optional[str] = None

    # Full audit trail of every status transition
    state_history: list[StateTransition] = Field(default_factory=list)

    archived_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "sessions"
