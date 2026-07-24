"""
Re-exports from the canonical backend schema module.
"""
import sys, os
import importlib.util

_backend_schema_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend/models/schema.py"))
_spec = importlib.util.spec_from_file_location("backend_schema", _backend_schema_path)
_backend_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_backend_schema)

FlowStatus = _backend_schema.FlowStatus
DiscoverySegment = _backend_schema.DiscoverySegment
DiscoveryProposedSolutionContext = _backend_schema.DiscoveryProposedSolutionContext
DiscoveryJobPayload = _backend_schema.DiscoveryJobPayload
DiscoveryJobMessage = _backend_schema.DiscoveryJobMessage
NotificationMessage = _backend_schema.NotificationMessage
DiscoveryDeadLetterMessage = _backend_schema.DiscoveryDeadLetterMessage
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
