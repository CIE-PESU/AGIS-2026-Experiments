"""
models/user.py — Beanie ODM model for the users collection.

Users are upserted on first login from PES Auth API data.
This document is the source of truth for user identity inside AGIS.
"""

from __future__ import annotations

from datetime import datetime, timezone

from beanie import Document
from pydantic import Field


class User(Document):
    """
    AGIS user document.

    Fields:
        srn             : PESU student registration number (unique).
        name            : Display name from PES Auth.
        email           : PESU email address.
        role            : "student" | "mentor" | "admin"
        team_id         : The team this student belongs to (None for mentors/admins).
        mentor_team_ids : Teams this mentor supervises (empty for students/admins).
        created_at      : First login timestamp.
        updated_at      : Last updated timestamp.
    """

    srn: str
    name: str
    email: str
    role: str
    team_id: str | None = None
    mentor_team_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        indexes = [
            [("srn", 1)],   # Unique lookup by SRN
            [("role", 1)],
        ]
