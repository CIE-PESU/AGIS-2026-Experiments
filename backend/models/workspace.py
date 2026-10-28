"""
models/workspace.py — Beanie ODM model for isolated 1:1 workspaces (`workspaces` collection).

Supports multiple workspace types (student, mentor, demo, external).
Stores magic token hashes, status, ownership, and admin lifecycle tracking.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class WorkspaceType(str, Enum):
    STUDENT = "student"
    MENTOR = "mentor"
    DEMO = "demo"
    EXTERNAL = "external"


class WorkspaceStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    ARCHIVED = "archived"


class Workspace(Document):
    """
    1:1 Isolated Workspace document.

    Fields:
        name                : Label or description for this workspace.
        type                : WorkspaceType ("student", "mentor", "demo", "external").
        status              : WorkspaceStatus ("active", "revoked", "archived").
        token_hash          : SHA-256 hash of the magic token string (for magic link access).
        student_user_id     : Student SRN or User ID (for student workspaces).
        created_by_admin_id : User ID of the admin who created this workspace link.
        created_at          : Creation timestamp.
        updated_at          : Update timestamp.
        revoked_at          : Revocation timestamp (if revoked).
    """

    name: str
    type: WorkspaceType = WorkspaceType.MENTOR
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE
    token_hash: Annotated[str, Indexed(unique=True)] | None = None
    student_user_id: Annotated[str, Indexed()] | None = None
    mentor_id: Annotated[str, Indexed()] | None = None
    created_by_admin_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    revoked_at: datetime | None = None

    class Settings:
        name = "workspaces"
        indexes = [
            IndexModel(
                [("token_hash", 1)],
                unique=True,
                name="uq_workspace_token",
                partialFilterExpression={"token_hash": {"$type": "string"}},
            ),
            IndexModel(
                [("student_user_id", 1)],
                unique=True,
                name="uq_active_student_workspace",
                partialFilterExpression={
                    "student_user_id": {"$type": "string"},
                    "status": "active",
                },
            ),
        ]

    @property
    def workspace_id(self) -> str:
        return str(self.id)

    @property
    def is_active(self) -> bool:
        return self.status == WorkspaceStatus.ACTIVE
