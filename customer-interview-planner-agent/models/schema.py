"""
Re-exports from the canonical backend schema module.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))
from models.schema import (   # noqa: F401 — re-export
    FlowStatus,
    DiscoverySegment,
    DiscoveryProposedSolutionContext,
    DiscoveryJobPayload,
    DiscoveryJobMessage,
    NotificationMessage,
    DiscoveryDeadLetterMessage,
)
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel

class DiscoveryResult(BaseModel):
    correlation_id: str
    status: FlowStatus
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
