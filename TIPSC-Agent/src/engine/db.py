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
