"""
backend/models/schema.py — Canonical Kafka message schemas.

Single source of truth for every message that crosses a Kafka topic boundary.
Both the backend and the agent workers import from here.

DFV-agent/models/schema.py and customer-interview-planner-agent/models/schema.py
should be updated to re-export from this module rather than define their own copies.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------

class FlowStatus(str, Enum):
    QUEUED  = "queued"
    RUNNING = "running"
    DONE    = "done"
    FAILED  = "failed"
    RETRY   = "retry"
    TIMEOUT = "timeout"


# ---------------------------------------------------------------------------
# Inbound: userSession.dfv
# ---------------------------------------------------------------------------

class DFVJobPayload(BaseModel):
    """Student-supplied context strings. Stored on the session before Kafka publish."""
    desirability_context: str = ""
    feasibility_context:  str = ""
    viability_context:    str = ""


class DFVJobMessage(BaseModel):
    """Message published by backend on POST /sessions/{id}/trigger/dfv."""
    userSession_id: str = Field(..., description="MongoDB _id string of the session")
    idea_name:      str = Field(default="", description="Human-readable idea label")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    retry_count:    int = Field(default=0)
    payload:        DFVJobPayload
    published_at:   datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Inbound: userSession.discovery
# ---------------------------------------------------------------------------

class DiscoverySegment(BaseModel):
    segment:       str
    role:          str
    customer_type: str


class DiscoveryProposedSolutionContext(BaseModel):
    purpose: str
    summary: str


class DiscoveryJobPayload(BaseModel):
    target_customer_segment:  list[DiscoverySegment]
    problem_statement:        str
    problem_consequence:      list[str]
    current_alternatives:     list[str]
    key_assumptions:          list[str]
    what_we_already_know:     list[str]
    biggest_uncertainty:      list[str]
    customer_type:            list[str]
    proposed_solution_context: DiscoveryProposedSolutionContext


class DiscoveryJobMessage(BaseModel):
    """Message published by backend on POST /sessions/{id}/trigger/discovery."""
    userSession_id: str = Field(..., description="MongoDB _id string of the session")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    retry_count:    int = Field(default=0)
    payload:        DiscoveryJobPayload
    published_at:   datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Inbound: userSession.pmf
# ---------------------------------------------------------------------------

class PMFJobPayload(BaseModel):
    idea_name:         str = ""
    problem_statement: str = ""
    proposed_solution: str = ""
    customer_segment:  str = ""


class PMFJobMessage(BaseModel):
    """Message published by backend on POST /sessions/{id}/trigger/pmf."""
    userSession_id: str = Field(..., description="MongoDB _id string of the session")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    retry_count:    int = Field(default=0)
    payload:        PMFJobPayload
    published_at:   datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Outbound: userSession.notifications (shared by DFV, Discovery, PMF workers)
# ---------------------------------------------------------------------------

class NotificationMessage(BaseModel):
    """Published by any worker on completion or failure."""
    userSession_id: str
    correlation_id: str
    flow:           str             # "dfv" | "discovery" | "pmf" | "tipsc"
    status:         FlowStatus
    idea_name:      Optional[str]  = None
    error:          Optional[str]  = None
    emitted_at:     datetime       = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Dead-letter queues
# ---------------------------------------------------------------------------

class DeadLetterMessage(BaseModel):
    """Published to userSession.dfv.dlq when DFV exceeds max retries."""
    original_message: DFVJobMessage
    failure_reason:   str
    failed_at:        datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DiscoveryDeadLetterMessage(BaseModel):
    """Published to userSession.discovery.dlq when Discovery exceeds max retries."""
    original_message: DiscoveryJobMessage
    failure_reason:   str
    failed_at:        datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
