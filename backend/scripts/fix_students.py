import asyncio
from core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.user import User

async def run():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[User])
    await User.find(User.role == 'student').update({"$set": {"team_id": None}})
    print("Fixed students")

asyncio.run(run())
