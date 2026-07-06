"""
DFV Kafka message schemas.

These define the contract between:
- Backend (publishes to userSession.dfv)
- DFV worker (consumes userSession.dfv, publishes to userSession.notifications)

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
# Inbound: userSession.dfv
# ---------------------------------------------------------------------------

class DFVJobPayload(BaseModel):
    """The DFV framework inputs a student submits (desirability / feasibility / viability context)."""
    desirability: str
    feasibility: str
    viability: str


class DFVJobMessage(BaseModel):
    """Message published by backend on POST /userSession/{id}/trigger/dfv"""
    userSession_id: str = Field(..., description="Mongo _id of the userSession")
    correlation_id: str = Field(..., description="Unique per-trigger id, used for tracing + idempotency")
    idea_name: str
    payload: DFVJobPayload
    retry_count: int = Field(default=0, description="Incremented by worker on each retry, not set by backend")
    published_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Outbound: userSession.notifications
# ---------------------------------------------------------------------------

class NotificationMessage(BaseModel):
    """Published by DFV worker on completion/failure so frontend poller picks it up."""
    userSession_id: str
    correlation_id: str
    flow: str = "dfv"
    status: FlowStatus
    idea_name: str
    error: Optional[str] = None
    emitted_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Outbound: userSession.dfv.dlq
# ---------------------------------------------------------------------------

class DeadLetterMessage(BaseModel):
    """Published when a job exceeds max retries."""
    original_message: DFVJobMessage
    failure_reason: str
    failed_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# MongoDB: userSession document — "dfv" sub-field (what the worker writes)
# ---------------------------------------------------------------------------
#
# NOTE: assumption until backend confirms their actual Pydantic models —
# a single `userSessions` collection, one document per session, with each
# flow (tipsc / dfv / discovery) as a sub-field. This matches the doc's
# "GET /userSession/{id} — return full session with flow statuses and
# outputs." The worker only ever touches its own `dfv` sub-field via
# $set, so it can't clobber other flows' data.

class DFVResult(BaseModel):
    correlation_id: str
    status: FlowStatus
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
