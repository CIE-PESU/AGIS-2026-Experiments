"""
One-time migration script for existing databases.
Synchronizes all active sessions so Session.team_id matches the student's User.team_id.

Usage:
  python backend/scripts/migrate_session_teams.py
"""

from __future__ import annotations

import asyncio
import logging
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from core.config import settings
from models.session import Session
from models.team import Team
from models.user import User
from state_machine.states import SessionStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    logger.info("Connecting to MongoDB: %s", settings.MONGODB_URI)
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=[User, Team, Session]
    )

    students = await User.find(User.role == "student").to_list()
    logger.info("Found %d students to process.", len(students))

    updated_count = 0
    for student in students:
        if not student.team_id:
            continue

        student_id_str = str(student.id)
        
        # Find active sessions whose team_id diverges from student.team_id
        diverged_sessions = await Session.find({
            "student_id": student_id_str,
            "team_id": {"$ne": student.team_id},
            "status": {"$ne": SessionStatus.ARCHIVED.value}
        }).to_list()

        for session in diverged_sessions:
            logger.info(
                "Updating Session %s (student: %s, SRN: %s) team_id: %s -> %s",
                session.id,
                student_id_str,
                student.srn,
                session.team_id,
                student.team_id
            )
            session.team_id = student.team_id
            await session.save()
            updated_count += 1

    logger.info("Migration complete. Total session documents updated: %d", updated_count)


if __name__ == "__main__":
    asyncio.run(migrate())
