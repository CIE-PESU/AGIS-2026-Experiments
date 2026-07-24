import asyncio
from core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.user import User
from models.team import Team

async def run():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[User, Team])
    teams = await Team.find_all().to_list()
    print("TEAMS:", [t.model_dump() for t in teams])
    students = await User.find(User.role == "student").to_list()
    print("STUDENTS:", [s.model_dump() for s in students])

asyncio.run(run())
