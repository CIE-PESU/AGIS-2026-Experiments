"""
schemas/session.py — Session request/response schemas.

API contract for the complete AGIS session lifecycle.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ─────────────────────────────────────────────────────────────────────────────
# TIPSC schemas
# ─────────────────────────────────────────────────────────────────────────────


class TIPSCRAGScoresSchema(BaseModel):
    T: str = ""
    IMPORTANT: str = ""
    P: str = ""
    S: str = ""

    T_reason: str = ""
    IMPORTANT_reason: str = ""
    P_reason: str = ""
    S_reason: str = ""


class TIPSCRefinedIdeaSchema(BaseModel):
    customer_segment: str = ""
    qualified_problem: str = ""
    consequence: str = ""
    proposed_solution: str = ""


class TIPSCOutputSchema(BaseModel):
    tips_rag_scores: TIPSCRAGScoresSchema = Field(default_factory=TIPSCRAGScoresSchema)

    refined_idea: TIPSCRefinedIdeaSchema = Field(default_factory=TIPSCRefinedIdeaSchema)

    solution_alignment: str = ""
    overall_readiness: str = ""

    ready_for_dfv: bool = False

    needs_followup: bool = False

    missing_criteria: list[str] = Field(default_factory=list)

    criteria_state: dict[str, Any] = Field(default_factory=dict)

    compliance_flag: bool = False

    reasoning: str = ""

    followups_asked: int = 0

    completed_at: datetime | None = None


# ─────────────────────────────────────────────────────────────────────────────
# DFV schemas
# ─────────────────────────────────────────────────────────────────────────────


class DFVOutputSchema(BaseModel):
    correlation_id: str = ""

    status: str = ""

    output: dict[str, Any] | None = None

    error: str | None = None

    retry_count: int = 0

    started_at: datetime | None = None

    completed_at: datetime | None = None

    idea_name: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Discovery schemas
# ─────────────────────────────────────────────────────────────────────────────


class DiscoveryOutputSchema(BaseModel):
    correlation_id: str = ""

    status: str = ""

    output: dict[str, Any] | None = None

    error: str | None = None

    retry_count: int = 0

    started_at: datetime | None = None

    completed_at: datetime | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Follow-up schemas
# ─────────────────────────────────────────────────────────────────────────────


class FollowupHistoryItemSchema(BaseModel):
    question: str
    answer: str


# ─────────────────────────────────────────────────────────────────────────────
# Session creation
# ─────────────────────────────────────────────────────────────────────────────


class SessionCreateRequest(BaseModel):
    """
    Initial pre-evaluation form.

    These are the default founder questions shown before TIPSC starts.
    """

    problem_statement: str = Field(
        ...,
        min_length=20,
        max_length=5000,
    )

    customer_segment: str = Field(
        ...,
        min_length=2,
        max_length=2000,
    )

    consequence: str = Field(
        ...,
        min_length=2,
        max_length=3000,
    )

    assumptions: list[str] = Field(
        default_factory=list,
    )

    proposed_solution: str = Field(
        ...,
        min_length=10,
        max_length=3000,
    )

    target_geography: str = Field(
        ...,
        min_length=2,
        max_length=1000,
    )

    industry_sector: str = Field(
        ...,
        min_length=2,
        max_length=1000,
    )

    team_id: str | None = None

    @field_validator(
        "problem_statement",
        "customer_segment",
        "consequence",
        "proposed_solution",
        "target_geography",
        "industry_sector",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, value: Any) -> str:
        return str(value).strip()

    @field_validator(
        "assumptions",
        mode="before",
    )
    @classmethod
    def normalize_assumptions(
        cls,
        value: Any,
    ) -> list[str]:

        if value is None:
            return []

        if isinstance(value, str):
            return [value.strip()]

        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]

        return []


# ─────────────────────────────────────────────────────────────────────────────
# Session response
# ─────────────────────────────────────────────────────────────────────────────


class SessionResponse(BaseModel):
    session_id: str

    student_id: str | None = None
    team_id: str | None = None
    workspace_id: str | None = None

    problem_statement: str
    idea: str

    preeval_input: dict[str, Any] | None = None

    status: str

    version: int

    # ── Pipeline intermediate state ───────────────────────────────────────

    preeval: dict[str, Any] | None = None

    validation: dict[str, Any] | None = None

    regulatory: dict[str, Any] | None = None

    ethics: dict[str, Any] | None = None

    compliance_context: str | None = None

    # ── Outputs ───────────────────────────────────────────────────────────

    tipsc: TIPSCOutputSchema | None = None

    dfv: DFVOutputSchema | None = None

    discovery: DiscoveryOutputSchema | None = None

    dfv_inputs: dict[str, str] | None = None

    discovery_inputs: dict[str, Any] | None = None

    # ── Follow-up state ───────────────────────────────────────────────────

    pending_question: str | None = None

    followup_turn: int = 0

    followup_history: list[FollowupHistoryItemSchema] = Field(default_factory=list)

    # ── Execution metadata ────────────────────────────────────────────────

    correlation_id: str | None = None

    error: str | None = None

    rejection_reason: str | None = None

    # ── Timestamps ────────────────────────────────────────────────────────

    created_at: datetime

    updated_at: datetime

    archived_at: datetime | None = None

    @classmethod
    def from_document(
        cls,
        session: Any,
    ) -> SessionResponse:
        return cls(
            session_id=str(session.id),
            student_id=session.student_id,
            team_id=session.team_id,
            workspace_id=session.workspace_id,
            problem_statement=session.problem_statement,
            idea=session.idea,
            preeval_input=session.preeval_input,
            status=(session.status.value if hasattr(session.status, "value") else session.status),
            version=session.version,
            preeval=session.preeval,
            validation=session.validation,
            regulatory=session.regulatory,
            ethics=session.ethics,
            compliance_context=session.compliance_context,
            tipsc=(
                TIPSCOutputSchema.model_validate(session.tipsc.model_dump())
                if session.tipsc
                else None
            ),
            dfv=(DFVOutputSchema.model_validate(session.dfv.model_dump()) if session.dfv else None),
            discovery=(
                DiscoveryOutputSchema.model_validate(session.discovery.model_dump())
                if session.discovery
                else None
            ),
            dfv_inputs=session.dfv_inputs.model_dump() if session.dfv_inputs else None,
            discovery_inputs=session.discovery_inputs.model_dump()
            if session.discovery_inputs
            else None,
            pending_question=session.pending_question,
            followup_turn=session.followup_turn,
            followup_history=[
                FollowupHistoryItemSchema.model_validate(item.model_dump())
                for item in (session.followup_history or [])
            ],
            correlation_id=session.correlation_id,
            error=session.error,
            rejection_reason=session.rejection_reason,
            created_at=session.created_at,
            updated_at=session.updated_at,
            archived_at=session.archived_at,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Session list response
# ─────────────────────────────────────────────────────────────────────────────


class SessionListResponse(SessionResponse):
    """
    Same shape as SessionResponse.

    Kept as a separate schema so the API contract can diverge later
    without modifying the detail endpoint.
    """

    @classmethod
    def from_document(
        cls,
        session: Any,
    ) -> SessionListResponse:

        response = SessionResponse.from_document(session)

        return cls(**response.model_dump())
