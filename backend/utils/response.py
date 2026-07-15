"""
utils/response.py — Standard response envelope builders.

Every successful API response wraps data in the envelope defined in api-spec.md Section 1.2:

  Success:
    { "data": {...}, "meta": { "request_id": "...", "timestamp": "..." } }

  Paginated:
    { "data": [...], "pagination": {...}, "meta": { ... } }

Use these helpers in every route handler to ensure consistency.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Request


def _meta(request: Request) -> dict:
    """Build the standard meta block with request_id and timestamp."""
    request_id = getattr(request.state, "request_id", "unknown")
    return {
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def success_response(data: Any, request: Request) -> dict:
    """
    Wrap a single resource or dict in the standard success envelope.

    Args:
        data    : The response payload (dict, list, or Pydantic model).
        request : The FastAPI request object (for request_id extraction).

    Returns:
        Standard success envelope: { "data": data, "meta": {...} }
    """
    return {
        "data": data,
        "meta": _meta(request),
    }


def paginated_response(
    data: list[Any],
    request: Request,
    page: int,
    limit: int,
    total: int,
) -> dict:
    """
    Wrap a list of items in the standard paginated success envelope.

    Args:
        data    : The list of items for the current page.
        request : The FastAPI request object.
        page    : Current page number (1-indexed).
        limit   : Number of items per page.
        total   : Total count of items across all pages.

    Returns:
        Paginated envelope: { "data": [...], "pagination": {...}, "meta": {...} }
    """
    return {
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "has_next": (page * limit) < total,
            "has_prev": page > 1,
        },
        "meta": _meta(request),
    }
