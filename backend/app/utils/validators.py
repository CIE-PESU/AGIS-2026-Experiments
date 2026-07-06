"""
utils/validators.py — Reusable field validators for AGIS backend.

These are used as Pydantic field_validators or standalone validation helpers
that can be imported by schema classes.
"""

from __future__ import annotations

import re
from typing import Any

from beanie import PydanticObjectId

# SRN regex pattern — matches PES<digit>UG<2 digits><2 uppercase letters><3 digits>
# Examples: PES2UG22CS001, PES1UG23EC047
_SRN_PATTERN = re.compile(r"^PES\dUG\d{2}[A-Z]{2}\d{3}$")


def validate_srn(srn: str) -> str:
    """
    Validate and normalize a SRN (Student Registration Number).

    Args:
        srn: Raw SRN string from the request.

    Returns:
        Uppercased, stripped SRN.

    Raises:
        ValueError: If the SRN does not match the expected format.
    """
    normalized = str(srn).upper().strip()
    if not _SRN_PATTERN.match(normalized):
        raise ValueError(
            "SRN must match the format PES<digit>UG<2 digits><2 uppercase letters><3 digits> "
            "(e.g. PES2UG22CS001)"
        )
    return normalized


def is_valid_object_id(value: Any) -> bool:
    """
    Check whether a string is a valid MongoDB ObjectId.

    Used to validate session_id and comment_id path parameters before
    hitting the database (prevents unnecessary DB round-trips for malformed IDs).
    """
    try:
        PydanticObjectId(str(value))
        return True
    except Exception:
        return False


def validate_object_id(value: str, field_name: str = "id") -> str:
    """
    Validate a path parameter as a MongoDB ObjectId.

    Args:
        value: The raw path parameter value.
        field_name: Name of the field (used in the error message).

    Returns:
        The validated string.

    Raises:
        ValueError: If value is not a valid ObjectId.
    """
    if not is_valid_object_id(value):
        raise ValueError(f"{field_name} must be a valid MongoDB ObjectId (24-character hex string).")
    return value
