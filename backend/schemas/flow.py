"""
Request/response schemas for the flow trigger endpoints.
Shapes match api-spec.md Section 4 exactly.
"""

from typing import Optional

from pydantic import BaseModel, Field
from models.schema import DiscoveryJobPayload
# The Discovery API accepts exactly the same payload that is
# published to Kafka. Keeping a single canonical schema prevents
# the backend and worker from drifting apart.
DiscoveryTriggerRequest = DiscoveryJobPayload


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

class FollowupAnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=5000)


