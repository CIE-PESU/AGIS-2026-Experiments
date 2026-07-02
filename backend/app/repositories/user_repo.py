"""
User repository — reads/writes the `users` collection.
upsert_from_pes is called on every successful login to keep user data current.
"""

from typing import Optional, Any
from datetime import datetime

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self) -> None:
        super().__init__(User)

    async def find_by_id(self, user_id: str) -> Optional[User]:
        """Fetch user by MongoDB _id."""
        return await User.get(user_id)

    async def find_by_srn(self, srn: str) -> Optional[User]:
        """Fetch user by SRN (unique per student)."""
        return await User.find_one(User.srn == srn)

    async def upsert_from_pes(self, pes_payload: dict[str, Any]) -> User:
        """
        Create or update a user document from PES Auth API response.
        Uses srn as the unique lookup key.
        Called on every successful login to keep name/email/role in sync with PES.
        """
        srn = pes_payload["srn"]
        existing = await self.find_by_srn(srn)

        if existing:
            existing.name = pes_payload.get("name", existing.name)
            existing.email = pes_payload.get("email", existing.email)
            existing.role = pes_payload.get("role", existing.role)
            existing.team_id = pes_payload.get("team_id", existing.team_id)
            existing.mentor_team_ids = pes_payload.get(
                "mentor_team_ids", existing.mentor_team_ids
            )
            await existing.save()
            return existing

        user = User(
            srn=srn,
            name=pes_payload["name"],
            email=pes_payload.get("email"),
            role=pes_payload["role"],
            team_id=pes_payload.get("team_id"),
            mentor_team_ids=pes_payload.get("mentor_team_ids", []),
        )
        await user.insert()
        return user


user_repo = UserRepository()
