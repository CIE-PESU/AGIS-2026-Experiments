"""
schemas/common.py — Shared Pydantic schemas used across all endpoints.

Matches api-spec.md Section 1.2 response envelope shapes exactly.

These schemas are used for:
  - Exception handlers (ErrorResponse)
  - Route handlers (BaseResponse, PaginatedResponse)
  - OpenAPI documentation (type hints on all routes)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

# Generic type for the data payload inside the envelope
DataT = TypeVar("DataT")


# ─────────────────────────────────────────────────────────────────────────────
# Meta Block (shared by success + error envelopes)
# ─────────────────────────────────────────────────────────────────────────────

class MetaBlock(BaseModel):
    """
    Standard meta block included in every response.
    Matches api-spec.md Section 1.2.
    """

    request_id: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pagination
# ─────────────────────────────────────────────────────────────────────────────

class PaginationMeta(BaseModel):
    """
    Pagination block included in all paginated list responses.
    Matches api-spec.md Section 1.2 paginated envelope.
    """

    page: int = Field(ge=1, description="Current page number (1-indexed).")
    limit: int = Field(ge=1, le=100, description="Items per page.")
    total: int = Field(ge=0, description="Total count of items across all pages.")
    has_next: bool
    has_prev: bool

    @classmethod
    def build(cls, page: int, limit: int, total: int) -> "PaginationMeta":
        """Factory helper to avoid repeating the has_next / has_prev logic everywhere."""
        return cls(
            page=page,
            limit=limit,
            total=total,
            has_next=(page * limit) < total,
            has_prev=page > 1,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Success Envelopes
# ─────────────────────────────────────────────────────────────────────────────

class BaseResponse(BaseModel, Generic[DataT]):
    """
    Standard single-resource success envelope.

    Usage:
        return BaseResponse[SessionResponse](data=session, meta=meta)

    Shape:
        { "data": {...}, "meta": { "request_id": "...", "timestamp": "..." } }
    """

    data: DataT
    meta: MetaBlock


class PaginatedResponse(BaseModel, Generic[DataT]):
    """
    Standard paginated list success envelope.

    Usage:
        return PaginatedResponse[CommentListItem](data=items, pagination=pg, meta=meta)

    Shape:
        { "data": [...], "pagination": {...}, "meta": {...} }
    """

    data: list[DataT]
    pagination: PaginationMeta
    meta: MetaBlock


# ─────────────────────────────────────────────────────────────────────────────
# Error Envelope
# ─────────────────────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    """
    Inner error object inside the error envelope.
    Matches api-spec.md Section 1.2 error shape.
    """

    code: str = Field(description="Catalog error code from api-spec.md Section 11.")
    message: str = Field(description="Human-readable error description.")
    field: Optional[str] = Field(
        default=None,
        description="For validation errors: the field that failed. Null otherwise.",
    )
    request_id: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ErrorResponse(BaseModel):
    """
    Standard error envelope for all 4xx / 5xx responses.

    Shape:
        {
          "error": {
            "code": "SESSION_NOT_FOUND",
            "message": "No session found with the given ID.",
            "field": null,
            "request_id": "uuid",
            "timestamp": "2026-06-01T10:00:00Z"
          }
        }
    """

    error: ErrorDetail
