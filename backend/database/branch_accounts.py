"""Provision this branch's shared accounts on a fresh database."""

import json
from datetime import UTC, datetime
from pathlib import Path

from bson import ObjectId


async def provision_branch_accounts(database) -> None:
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    accounts = json.loads((scripts / "branch_accounts.json").read_text(encoding="utf-8"))
    seed = json.loads((scripts / "seed_data.json").read_text(encoding="utf-8"))
    seed_ids = {user["srn"]: ObjectId(user["id"]) for user in seed["users"]}
    for account in accounts:
        # Preserve IDs, assignments and subsequent password changes on existing accounts.
        await database.users.update_one(
            {"srn": account["srn"]},
            {
                "$setOnInsert": {
                    **account,
                    **({"_id": seed_ids[account["srn"]]} if account["srn"] in seed_ids else {}),
                    "encrypted_password": None,
                    "email": None,
                    "team_id": None,
                    "mentor_team_ids": [],
                    "created_at": datetime.now(UTC),
                }
            },
            upsert=True,
        )
        # Metadata imports can create accounts before the first application start.
        # Fill only missing credentials; never replace a deliberately changed password.
        await database.users.update_one(
            {"srn": account["srn"], "password_hash": None, "encrypted_password": None},
            {"$set": {"password_hash": account["password_hash"]}},
        )
