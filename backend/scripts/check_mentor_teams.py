import asyncio
import json
from core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.team import Team
from models.user import User

async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[Team, User])
    teams = await Team.find_all().to_list()
    mentors = await User.find(User.role == "mentor").to_list()
    print("Teams:", [{'id': str(t.id), 'mentor_id': t.mentor_id} for t in teams])
    print("Mentors:", [{'id': str(m.id), 'srn': m.srn} for m in mentors])

asyncio.run(main())
