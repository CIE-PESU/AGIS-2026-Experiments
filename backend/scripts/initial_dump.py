import asyncio

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from core.config import settings
from core.sync import dump_seed_data
from models.team import Team
from models.user import User


async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[User, Team])
    await dump_seed_data()
    print("Dumped seed data.")

asyncio.run(main())
