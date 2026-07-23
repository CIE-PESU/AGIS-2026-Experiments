import asyncio
from core.sync import dump_seed_data
from core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.user import User
from models.team import Team

async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[User, Team])
    await dump_seed_data()
    print("Dumped seed data.")

asyncio.run(main())
