import asyncio

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from core.config import settings
from models.user import User


async def run():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[User])
    users = await User.find(User.role == "student").to_list()
    for u in users:
        u.team_id = None
        await u.save()
    print("Cleared all student team associations")


asyncio.run(run())
