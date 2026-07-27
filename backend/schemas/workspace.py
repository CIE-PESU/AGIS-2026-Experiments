"""
schemas/workspace.py — Pydantic request/response schemas for Workspace management & magic link access.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class WorkspaceCreateRequest(BaseModel):
    """POST /admin/workspaces request body."""

    name: str = Field(description="Name or description for this workspace link.")
    mentor_id: Optional[str] = Field(default=None, description="Optional Mentor ID associated with this workspace.")


class WorkspaceResponse(BaseModel):
    """Response payload for a single Workspace entity."""

    workspace_id: str
    name: str
    type: str
    status: str
    mentor_id: Optional[str] = None
    magic_url: Optional[str] = None
    created_at: str
    revoked_at: Optional[str] = None


class WorkspaceAccessRequest(BaseModel):
    """POST /workspace/access request body."""

    token: str = Field(description="Raw magic token string extracted from URL.")


class WorkspaceAccessResponse(BaseModel):
    """Success payload for POST /workspace/access."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    role: str = "mentor_workspace"
    workspace_id: str
    name: str
