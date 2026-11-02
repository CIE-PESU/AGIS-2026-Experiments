"""Read bounded, credential-free database metadata. Use admin APIs for mutations."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import settings  # noqa: E402


async def inspect(collection: str, limit: int) -> None:
    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URI)
    try:
        database = client[settings.MONGODB_DB_NAME]
        projection = {"password_hash": 0, "encrypted_password": 0}
        records = await database[collection].find({}, projection).limit(limit).to_list(length=limit)
        print(json.dumps(records, indent=2, default=str))
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", choices=["users", "teams"], default="teams")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("--limit must be between 1 and 1000")
    asyncio.run(inspect(args.collection, args.limit))


if __name__ == "__main__":
    main()
