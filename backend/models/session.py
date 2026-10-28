"""
models/session.py — MongoDB session document.

Source of truth for the complete AGIS session lifecycle.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from beanie import Document, Indexed
from pydantic import AliasChoices, BaseModel, Field, model_validator
from pymongo import ASCENDING, DESCENDING, IndexModel

from models.schema import DiscoveryJobPayload
from state_machine.states import SessionStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


# ─────────────────────────────────────────────────────────────────────────────
# State transition
# ─────────────────────────────────────────────────────────────────────────────


class StateTransition(BaseModel):
    from_status: str = ""
    to_status: str
    timestamp: datetime = Field(default_factory=utc_now)
    actor: str = "system"
    trigger: str = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# TIPSC embedded models
# ─────────────────────────────────────────────────────────────────────────────


class TIPSCRefinedIdea(BaseModel):
    customer_segment: str = ""
    qualified_problem: str = ""
    consequence: str = ""
    proposed_solution: str = ""


class TIPSValidatedMetrics(BaseModel):
    timely_factor: str = ""
    importance_metric: str = ""
    profitability_pivot: str = ""
    solvability_constraint: str = ""


class TIPSCRAGScores(BaseModel):
    T: str = ""
    IMPORTANT: str = Field(default="", validation_alias=AliasChoices("IMPORTANT", "I"))
    P: str = ""
    S: str = ""

    T_reason: str = ""
    IMPORTANT_reason: str = Field(
        default="", validation_alias=AliasChoices("IMPORTANT_reason", "I_reason")
    )
    P_reason: str = ""
    S_reason: str = ""

    @model_validator(mode="before")
    @classmethod
    def handle_case_insensitivity(cls, data: dict):
        if not isinstance(data, dict):
            return data

        # Check for lowercase or capitalized variants of reason fields
        for letter in ["T", "I", "P", "S"]:
            upper_key = f"{letter}_reason"
            lower_key = f"{letter.lower()}_reason"
            title_key = f"{letter}_Reason"

            # If the correct key is missing, try to find an alternative
            if upper_key not in data or not data[upper_key]:
                if lower_key in data and data[lower_key]:
                    data[upper_key] = data[lower_key]
                elif title_key in data and data[title_key]:
                    data[upper_key] = data[title_key]

        return data


class TIPSCOutput(BaseModel):
    """
    Persisted TIPSC result.

    Must remain compatible with:
        TIPSC-Agent/src/models.py:TIPSCOutput

    Backend-only metadata fields are also included.
    """

    refined_idea: TIPSCRefinedIdea = Field(default_factory=TIPSCRefinedIdea)

    solution_alignment: str = ""

    tips_validated_metrics: TIPSValidatedMetrics = Field(default_factory=TIPSValidatedMetrics)

    tips_rag_scores: TIPSCRAGScores = Field(default_factory=TIPSCRAGScores)

    overall_readiness: str = ""

    ready_for_dfv: bool = False

    needs_followup: bool = False

    missing_criteria: list[str] = Field(default_factory=list)

    criteria_state: dict[str, Any] = Field(default_factory=dict)

    # Backend enrichment fields

    compliance_flag: bool = False

    reasoning: str = ""

    followups_asked: int = 0

    completed_at: datetime | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Follow-up models
# ─────────────────────────────────────────────────────────────────────────────


class FollowupExchange(BaseModel):
    """
    One completed founder follow-up exchange.

    pending_question is stored separately until answered.
    Only answered questions appear in followup_history.
    """

    question: str
    answer: str

    turn: int

    answered_at: datetime = Field(default_factory=utc_now)


# ─────────────────────────────────────────────────────────────────────────────
# DFV models
# ─────────────────────────────────────────────────────────────────────────────


class DFVInputs(BaseModel):
    desirability_context: str
    feasibility_context: str
    viability_context: str


class DFVOutput(BaseModel):
    """
    DFV worker output.

    Kept flexible because the combined agent worker stores its raw
    structured output inside `output`.
    """

    correlation_id: str = ""

    status: str = ""

    output: dict[str, Any] | None = None

    error: str | None = None

    retry_count: int = 0

    started_at: datetime | None = None

    completed_at: datetime | None = None

    idea_name: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Discovery models
# ─────────────────────────────────────────────────────────────────────────────


class DiscoveryOutput(BaseModel):
    correlation_id: str = ""

    status: str = ""

    output: dict[str, Any] | None = None

    error: str | None = None

    retry_count: int = 0

    started_at: datetime | None = None

    completed_at: datetime | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Worker failure metadata
# ─────────────────────────────────────────────────────────────────────────────


class WorkerFailureMetadata(BaseModel):
    flow: str

    error_code: str

    error_message: str

    retry_count: int = 0

    failed_at: datetime = Field(default_factory=utc_now)


# ─────────────────────────────────────────────────────────────────────────────
# Session document
# ─────────────────────────────────────────────────────────────────────────────


class Session(Document):
    # ── Ownership ──────────────────────────────────────────────────────────

    student_id: Annotated[str, Indexed()] | None = None

    team_id: Annotated[str, Indexed()] | None = None

    workspace_id: Annotated[str, Indexed()] | None = None

    # ── Founder input ──────────────────────────────────────────────────────

    problem_statement: str

    # Compatibility field used by DFV / Discovery.
    # Contains proposed_solution.
    idea: str

    # Complete seven-field PreEval founder input.
    preeval_input: dict[str, Any] | None = None

    # ── Pipeline state ─────────────────────────────────────────────────────

    status: SessionStatus = SessionStatus.CREATED

    version: int = 0

    # ── TIPSC intermediate state ───────────────────────────────────────────

    preeval: dict[str, Any] | None = None

    validation: dict[str, Any] | None = None

    regulatory: dict[str, Any] | None = None

    ethics: dict[str, Any] | None = None

    compliance_context: str | None = None

    # ── Flow outputs ───────────────────────────────────────────────────────

    tipsc: TIPSCOutput | None = None

    dfv: DFVOutput | None = None

    discovery: DiscoveryOutput | None = None

    # ── DFV founder context ────────────────────────────────────────────────

    dfv_inputs: DFVInputs | None = None

    # ── Discovery founder context ─────────────────────────────────────────

    discovery_inputs: DiscoveryJobPayload | None = None

    # ── TIPSC founder follow-up state ──────────────────────────────────────

    # Question currently visible to the frontend.
    pending_question: str | None = None

    # Kept for compatibility.
    # Answers should normally be written directly to followup_history.
    pending_answer: str | None = None

    # Current question turn.
    # 0 = no question generated.
    # 1..3 = active follow-up turn.
    followup_turn: int | None = 0

    # Only completed Q&A exchanges.
    followup_history: list[FollowupExchange] = Field(default_factory=list)

    # ── Execution metadata ─────────────────────────────────────────────────

    correlation_id: str | None = None
    flow_requests: dict[str, dict[str, Any]] = Field(default_factory=dict)

    flow_started_at: datetime | None = None

    failure_metadata: WorkerFailureMetadata | None = None

    error: str | None = None

    rejection_reason: str | None = None

    # ── Idempotency / audit ────────────────────────────────────────────────

    idempotency_key: str | None = None

    state_history: list[StateTransition] = Field(default_factory=list)

    # ── Lifecycle timestamps ───────────────────────────────────────────────

    archived_at: datetime | None = None

    created_at: datetime = Field(default_factory=utc_now)

    updated_at: datetime = Field(default_factory=utc_now)

    # ── MongoDB configuration ──────────────────────────────────────────────

    class Settings:
        name = "sessions"

        indexes = [
            IndexModel(
                [("workspace_id", ASCENDING)],
                name="uq_active_workspace_id",
                unique=True,
                partialFilterExpression={
                    "workspace_id": {"$type": "string"},
                    "status": {
                        "$in": [s.value for s in SessionStatus if s != SessionStatus.ARCHIVED]
                    },
                },
            ),
            IndexModel(
                [("student_id", ASCENDING)],
                name="uq_active_student_id",
                unique=True,
                partialFilterExpression={
                    "student_id": {"$type": "string"},
                    "status": {
                        "$in": [s.value for s in SessionStatus if s != SessionStatus.ARCHIVED]
                    },
                },
            ),
            IndexModel(
                [("workspace_id", ASCENDING)],
                name="ix_sessions_workspace_id",
            ),
            IndexModel(
                [
                    ("workspace_id", ASCENDING),
                    ("status", ASCENDING),
                ],
                name="ix_sessions_workspace_status",
            ),
            IndexModel(
                [
                    ("workspace_id", ASCENDING),
                    ("created_at", DESCENDING),
                ],
                name="ix_sessions_workspace_created",
            ),
            IndexModel(
                [("student_id", ASCENDING)],
                name="ix_sessions_student_id",
            ),
            IndexModel(
                [("team_id", ASCENDING)],
                name="ix_sessions_team_id",
            ),
            IndexModel(
                [("status", ASCENDING)],
                name="ix_sessions_status",
            ),
            IndexModel(
                [
                    ("student_id", ASCENDING),
                    ("status", ASCENDING),
                ],
                name="ix_sessions_student_status",
            ),
            IndexModel(
                [("created_at", DESCENDING)],
                name="ix_sessions_created_at_desc",
            ),
            IndexModel(
                [("idempotency_key", ASCENDING)],
                name="ix_sessions_idempotency_key",
                unique=True,
                sparse=True,
            ),
        ]
