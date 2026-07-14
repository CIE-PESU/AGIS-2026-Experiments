"""
Re-exports from the canonical backend schema module.
The backend/models/schema.py is the single source of truth.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))
from models.schema import (   # noqa: F401 — re-export
    FlowStatus,
    DFVJobPayload,
    DFVJobMessage,
    NotificationMessage,
    DeadLetterMessage,
)
# DFVResult is DFV-agent-specific (not shared):
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel

class DFVResult(BaseModel):
    correlation_id: str
    status: FlowStatus
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
