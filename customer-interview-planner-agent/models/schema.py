"""
Discovery (Customer Discovery Planner / JTBD) Kafka message schemas.

These define the contract between:
- Backend (publishes to userSession.discovery)
- Discovery worker (consumes userSession.discovery, publishes to
  userSession.notifications)

This project is self-contained — separate from DFV-agent/, even though
both publish to the same shared userSession.notifications topic and
write into the same userSessions Mongo collection (each into its own
sub-field, so they never collide).

Any change here must be agreed with the backend team before merging.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class FlowStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    RETRY = "retry"
    TIMEOUT = "timeout"


# ---------------------------------------------------------------------------
# Inbound: userSession.discovery
# ---------------------------------------------------------------------------
#
# Shape mirrors customer_interview_planner.py's SAMPLE_DISCOVERY_INPUTS.
# In production this comes from the student's PS/TIPSC/DFV submissions
# already stored on the userSession document — backend assembles this
# payload before publishing, the student doesn't type it fresh.

class DiscoverySegment(BaseModel):
    segment: str
    role: str
    customer_type: str


class DiscoveryProposedSolutionContext(BaseModel):
    purpose: str
    summary: str


class DiscoveryJobPayload(BaseModel):
    target_customer_segment: list[DiscoverySegment]
    problem_statement: str
    problem_consequence: list[str]
    current_alternatives: list[str]
    key_assumptions: list[str]
    what_we_already_know: list[str]
    biggest_uncertainty: list[str]
    customer_type: list[str]
    proposed_solution_context: DiscoveryProposedSolutionContext


class DiscoveryJobMessage(BaseModel):
    """Message published by backend on POST /userSession/{id}/trigger/discovery"""
    userSession_id: str = Field(..., description="Mongo _id of the userSession")
    correlation_id: str = Field(..., description="Unique per-trigger id, used for tracing + idempotency")
    payload: DiscoveryJobPayload
    retry_count: int = Field(default=0, description="Incremented by worker on each retry, not set by backend")
    published_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Outbound: userSession.notifications (shared topic with DFV worker)
# ---------------------------------------------------------------------------
#
# idea_name is Optional and left as None here — Discovery jobs don't have
# a single "idea name" the way DFV jobs do (DFV-agent's copy of this same
# class sets it; keep both copies' field shapes in sync since they share
# a topic).

class NotificationMessage(BaseModel):
    """Published by the Discovery worker on completion/failure so frontend poller picks it up."""
    userSession_id: str
    correlation_id: str
    flow: str = "discovery"
    status: FlowStatus
    idea_name: Optional[str] = None
    error: Optional[str] = None
    emitted_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Outbound: userSession.discovery.dlq
# ---------------------------------------------------------------------------

class DiscoveryDeadLetterMessage(BaseModel):
    """Published when a Discovery job exceeds max retries."""
    original_message: DiscoveryJobMessage
    failure_reason: str
    failed_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# MongoDB: userSession document — "discovery" sub-field
# ---------------------------------------------------------------------------
#
# NOTE: assumption until backend confirms their actual Pydantic models —
# a single `userSessions` collection (shared with DFV and TIPSC), one
# document per session, each flow as its own sub-field. This worker only
# ever touches its own "discovery" sub-field via $set.

class DiscoveryResult(BaseModel):
    correlation_id: str
    status: FlowStatus
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
