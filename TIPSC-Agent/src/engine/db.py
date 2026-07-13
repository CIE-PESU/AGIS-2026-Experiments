"""Async MongoDB wrapper for pipeline state reads/writes."""

from datetime import datetime


class SessionStore:

    def __init__(self, collection):
        self._collection = collection

    async def update_session(self, session_id: str, patch: dict):
        await self._collection.update_one(
            {"_id": session_id},
            {"$set": patch},
            upsert=True,
        )

    async def get_session(self, session_id: str) -> dict | None:
        return await self._collection.find_one({"_id": session_id})

    async def get_active_session_by_user(self, student_id: str) -> dict | None:
        """Find the most recent WAITING_FOR_FOUNDER session for a user."""
        return await self._collection.find_one(
            {
                "student_id": student_id,
                "state": "WAITING_FOR_FOUNDER",
            },
            sort=[("updated_at", -1)],
        )
