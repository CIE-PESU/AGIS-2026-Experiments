"""
User Beanie ODM model — `users` collection.
One document per authenticated PESU user.
"""

from datetime import datetime
from typing import Optional
from beanie import Document
from pydantic import Field


class User(Document):
    srn: str
    name: str
    email: Optional[str] = None
    role: str  # "student" | "mentor" | "admin"
    team_id: Optional[str] = None          # set for students
    mentor_team_ids: list[str] = Field(default_factory=list)  # set for mentors
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
