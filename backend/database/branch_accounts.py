"""Provision this branch's shared accounts on a fresh database."""

import json
from datetime import UTC, datetime
from pathlib import Path


async def provision_branch_accounts(database) -> None:
    accounts = json.loads(
        (Path(__file__).resolve().parents[1] / "scripts" / "branch_accounts.json").read_text(
            encoding="utf-8"
        )
    )
    for account in accounts:
        # Preserve IDs, assignments and subsequent password changes on existing accounts.
        await database.users.update_one(
            {"srn": account["srn"]},
            {
                "$setOnInsert": {
                    **account,
                    "encrypted_password": None,
                    "email": None,
                    "team_id": None,
                    "mentor_team_ids": [],
                    "created_at": datetime.now(UTC),
                }
            },
            upsert=True,
        )
