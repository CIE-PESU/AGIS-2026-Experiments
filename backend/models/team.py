"""
Team Beanie ODM model — `teams` collection.
One document per student team.
"""

from datetime import UTC, datetime

from beanie import Document
from pydantic import Field


class Team(Document):
    team_name: str
    mentor_id: str  # user_id of the assigned mentor
    members: list[str] = Field(default_factory=list)  # list of user_ids
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "teams"
