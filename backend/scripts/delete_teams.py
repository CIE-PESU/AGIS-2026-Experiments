import asyncio
from core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.team import Team

async def run():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[Team])
    await Team.find_all().delete()
    print("Deleted all teams")

asyncio.run(run())
