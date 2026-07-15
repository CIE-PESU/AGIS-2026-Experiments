"""
utils/pagination.py — Pagination utility helpers.

Provides helpers for computing pagination metadata from a
(page, limit, total) triple.
"""

from __future__ import annotations


def compute_pagination(page: int, limit: int, total: int) -> dict:
    """
    Build a standard pagination metadata block.

    Args:
        page  : Current page number (1-indexed).
        limit : Max items per page.
        total : Total count of matching items across all pages.

    Returns:
        Dict with keys: page, limit, total, has_next, has_prev.
    """
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "has_next": (page * limit) < total,
        "has_prev": page > 1,
    }
