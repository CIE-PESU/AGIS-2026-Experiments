"""
Request/response schemas for the flow trigger endpoints.
Shapes match api-spec.md Section 4 exactly.
"""

from pydantic import BaseModel, Field


class DFVTriggerRequest(BaseModel):
    desirability_context: str = Field(..., min_length=100, max_length=3000)
    feasibility_context: str = Field(..., min_length=100, max_length=3000)
    viability_context: str = Field(..., min_length=100, max_length=3000)


class FlowTriggerResponse(BaseModel):
    session_id: str
    flow: str  # "tipsc" | "dfv" | "discovery"
    status: str
    correlation_id: str | None
    triggered_at: str