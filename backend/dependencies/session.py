"""
dependencies/session.py — Session-scoped FastAPI dependencies.

Provides reusable dependencies for validating session access
at the dependency injection layer, so route handlers stay clean.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Path

from exceptions.base import ValidationException
from utils.validators import is_valid_object_id


async def validate_session_id(
    session_id: str = Path(..., description="Session ID (MongoDB ObjectId)."),
) -> str:
    """
    FastAPI path dependency that validates session_id is a valid ObjectId format.
    Prevents malformed IDs from hitting the database.

    Usage:
        @router.get("/{session_id}")
        async def get_session(session_id: str = Depends(validate_session_id)):
            ...
    """
    if not is_valid_object_id(session_id):
        raise ValidationException(
            message=f"session_id '{session_id}' is not a valid MongoDB ObjectId.",
            field="session_id",
        )
    return session_id
