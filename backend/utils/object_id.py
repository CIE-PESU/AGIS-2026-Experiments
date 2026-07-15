"""
utils/object_id.py — ObjectId format validation helper.

B-21: session_id path parameters must be valid MongoDB ObjectId strings
(24-character hex strings). Invalid IDs should return 400 VALIDATION_ERROR
before hitting the database, not 500 or a cryptic pymongo error.
"""

from __future__ import annotations

import re

from exceptions.base import ValidationException

# MongoDB ObjectId: exactly 24 hex characters
_OBJECT_ID_RE = re.compile(r"^[a-f0-9]{24}$", re.IGNORECASE)


def validate_object_id(value: str, field: str = "session_id") -> str:
    """
    Raise ValidationException (400) if `value` is not a valid MongoDB ObjectId.

    Returns the validated string unchanged so callers can do:
        session_id = validate_object_id(session_id)

    Args:
        value: The string to validate.
        field: Field name used in the error message (default: "session_id").
    """
    if not _OBJECT_ID_RE.match(value):
        raise ValidationException(
            message=f"'{field}' must be a valid 24-character hex ObjectId.",
            field=field,
        )
    return value
