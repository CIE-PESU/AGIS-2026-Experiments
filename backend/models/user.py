"""
User Beanie ODM model — `users` collection.
One document per authenticated PESU user.
"""

from datetime import UTC, datetime

from beanie import Document
from pydantic import Field


class User(Document):
    srn: str
    name: str
    email: str | None = None
    role: str  # "student" | "mentor" | "admin"
    password_hash: str | None = None
    encrypted_password: str | None = None
    team_id: str | None = None  # set for students
    mentor_team_ids: list[str] = Field(default_factory=list)  # set for mentors
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "users"
