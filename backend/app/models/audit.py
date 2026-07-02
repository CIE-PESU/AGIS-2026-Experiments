"""
AuditLog Beanie ODM model — `audit_logs` collection.
Append-only — never updated or deleted.
"""

from datetime import datetime
from typing import Any, Optional
from beanie import Document
from pydantic import Field


class AuditLog(Document):
    session_id: Optional[str] = None   # null for auth events (login, logout)
    event: str                          # e.g. SESSION_CREATED, TIPSC_TRIGGERED
    actor: str                          # user_id or "system" or "worker_tipsc"
    actor_role: str                     # "student" | "mentor" | "admin" | "worker" | "system"
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "audit_logs"
