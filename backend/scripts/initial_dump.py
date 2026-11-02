import asyncio
import sys
from pathlib import Path

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import settings  # noqa: E402
from core.sync import dump_seed_data  # noqa: E402
from models.team import Team  # noqa: E402
from models.user import User  # noqa: E402


async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    try:
        await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[User, Team])
        await dump_seed_data()
    finally:
        client.close()
    print("Sanitized export complete if AGIS_EXPORT_PATH was configured.")


if __name__ == "__main__":
    asyncio.run(main())
