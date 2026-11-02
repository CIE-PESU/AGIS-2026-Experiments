"""Synchronize active session team IDs from user records, including unassigned users.

Run with the API and worker stopped:
    uv run python -m backend.scripts.migrate_session_teams
"""

import asyncio
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import settings  # noqa: E402


async def migrate() -> None:
    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URI)
    try:
        database = client[settings.MONGODB_DB_NAME]
        count = 0
        async for student in database.users.find({"role": "student"}):
            team_id = student.get("team_id") or ""
            result = await database.sessions.update_many(
                {
                    "student_id": str(student["_id"]),
                    "team_id": {"$ne": team_id},
                    "status": {"$ne": "archived"},
                },
                {"$set": {"team_id": team_id}, "$inc": {"version": 1}},
            )
            count += result.modified_count
        print(f"Updated {count} active session team references.")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(migrate())
