import asyncio
from core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.team import Team

async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[Team])
    teams = await Team.find_all().to_list()
    print("Teams:", teams)

asyncio.run(main())
