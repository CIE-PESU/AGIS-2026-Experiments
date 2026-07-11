"""
schemas/comment.py — Pydantic request/response schemas for Comment APIs.

Matches api-spec.md Section 6 exactly.

Endpoints:
  POST   /sessions/{session_id}/comments  → CommentCreateRequest / CommentResponse
  GET    /sessions/{session_id}/comments  → list[CommentListItem]
  DELETE /comments/{comment_id}           → 204 No Content (no schema needed)
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Request Schemas
# ─────────────────────────────────────────────────────────────────────────────

class CommentCreateRequest(BaseModel):
    """
    POST /sessions/{session_id}/comments request body.

    Validation (from api-spec.md Section 6.1):
      - comment: min 10 chars, max 2000 chars
    """

    comment: Annotated[
        str,
        Field(
            min_length=10,
            max_length=2000,
            description="Mentor feedback. Min 10 chars, max 2000 chars.",
        ),
    ]

    @field_validator("comment", mode="before")
    @classmethod
    def strip_comment(cls, v: str) -> str:
        """Strip leading/trailing whitespace before length check."""
        return str(v).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Response Schemas
# ─────────────────────────────────────────────────────────────────────────────

class CommentResponse(BaseModel):
    """
    Full comment shape — returned on POST /sessions/{session_id}/comments.
    Matches api-spec.md Section 6.1 response.
    """

    comment_id: str
    session_id: str
    mentor_id: str
    mentor_name: str
    comment: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentListItem(BaseModel):
    """
    Summary comment shape — returned in GET /sessions/{session_id}/comments list.
    Matches api-spec.md Section 6.2 response (mentor_id excluded from list view).
    """

    comment_id: str
    mentor_name: str
    comment: str
    created_at: datetime

    model_config = {"from_attributes": True}
