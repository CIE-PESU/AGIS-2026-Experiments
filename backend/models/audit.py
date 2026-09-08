"""
AuditLog Beanie ODM model — `audit_logs` collection.
Append-only — never updated or deleted.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from beanie import Document
from pydantic import Field


class AuditEvent(str, Enum):
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_ARCHIVED = "SESSION_ARCHIVED"
    TIPSC_TRIGGERED = "TIPSC_TRIGGERED"
    TIPSC_COMPLETED = "TIPSC_COMPLETED"
    TIPSC_FAILED = "TIPSC_FAILED"
    DFV_TRIGGERED = "DFV_TRIGGERED"
    DFV_COMPLETED = "DFV_COMPLETED"
    DFV_FAILED = "DFV_FAILED"
    DISCOVERY_TRIGGERED = "DISCOVERY_TRIGGERED"
    DISCOVERY_COMPLETED = "DISCOVERY_COMPLETED"
    DISCOVERY_FAILED = "DISCOVERY_FAILED"
    PMF_TRIGGERED = "PMF_TRIGGERED"
    PMF_COMPLETED = "PMF_COMPLETED"
    PMF_FAILED = "PMF_FAILED"
    COMMENT_ADDED = "COMMENT_ADDED"
    COMMENT_DELETED = "COMMENT_DELETED"
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"


class AuditLog(Document):
    session_id: Optional[str] = None   # null for auth events (login, logout)
    event: AuditEvent                  # Event enum
    actor: Optional[str] = None        # user_id or "system" or "ws_{workspace_id}"
    actor_role: Optional[str] = "system" # "student" | "mentor" | "mentor_workspace" | "admin" | "worker" | "system"
    workspace_id: Optional[str] = None # Workspace ID for External Reviewers / guest workspace sessions
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "audit_logs"
