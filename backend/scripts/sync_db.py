"""Import sanitized metadata with stable IDs and preserve existing credentials.

Run from the repository root:
    uv run python -m backend.scripts.sync_db --file /private/path/accounts.json
Add --apply to write the metadata. The default only validates the file.
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import settings  # noqa: E402
from schemas.seed import SeedData  # noqa: E402


async def sync(seed_file: Path, *, apply: bool = False) -> None:
    data = SeedData.model_validate_json(seed_file.read_text(encoding="utf-8"))
    print(f"Validated {len(data.users)} users and {len(data.teams)} teams.")
    if not apply:
        print("No writes made. Add --apply to import this metadata.")
        return

    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URI)
    try:
        database = client[settings.MONGODB_DB_NAME]
        users = {str(row["_id"]): row async for row in database.users.find()}
        teams = {str(row["_id"]): row async for row in database.teams.find()}
        srns = {row["srn"].strip().upper(): key for key, row in users.items()}
        # Reject identity collisions before writing any records.
        for user in data.users:
            if user.srn in srns and srns[user.srn] != user.id:
                raise ValueError("An imported SRN already belongs to a different user ID")
            if user.id in users and users[user.id]["srn"].strip().upper() != user.srn:
                raise ValueError("An imported user ID already belongs to a different SRN")
            users[user.id] = {**users.get(user.id, {}), **user.model_dump(exclude_unset=True)}
        for team in data.teams:
            teams[team.id] = {**teams.get(team.id, {}), **team.model_dump(exclude_unset=True)}
        users_by_srn = {user["srn"].strip().upper(): user for user in users.values()}
        for team_id, team in teams.items():
            mentor = users.get(team.get("mentor_id", ""))
            if team.get("mentor_id") and (not mentor or mentor["role"] != "mentor"):
                raise ValueError("Every team must reference an existing mentor")
            for member_srn in team.get("members", []):
                member = users_by_srn.get(member_srn)
                if not member or member["role"] != "student" or member.get("team_id") != team_id:
                    raise ValueError("Team members must reference students with matching team_id")
        for user in users.values():
            team_id = user.get("team_id")
            if team_id and (
                team_id not in teams or user["srn"] not in teams[team_id].get("members", [])
            ):
                raise ValueError("Student team_id must reference a team containing that student")

        for collection, records in ((database.users, data.users), (database.teams, data.teams)):
            for record in records:
                updates = record.model_dump(exclude={"id"}, exclude_unset=True)
                # Omitted optional fields never clear existing associations.
                if updates.get("created_at") is None:
                    updates.pop("created_at", None)
                defaults = {} if "created_at" in updates else {"created_at": datetime.now(UTC)}
                await collection.update_one(
                    {"_id": ObjectId(record.id)},
                    {"$set": updates, "$setOnInsert": defaults},
                    upsert=True,
                )
        print("Metadata imported. Existing credentials were preserved.")
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=Path(__file__).with_name("seed_data.json"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(sync(args.file, apply=args.apply))


if __name__ == "__main__":
    main()
