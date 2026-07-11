"""
MentorComment Beanie ODM model — `mentor_comments` collection.
Supports soft-delete (deleted flag). Comments are never hard-deleted.
"""

from datetime import datetime
from beanie import Document
from pydantic import Field


class MentorComment(Document):
    session_id: str
    mentor_id: str
    mentor_name: str
    comment: str
    deleted: bool = False   # soft-delete — excluded from queries when True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "mentor_comments"
