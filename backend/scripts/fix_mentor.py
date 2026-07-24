import asyncio
from core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.team import Team
from models.user import User

async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[Team, User])
    p = await User.find_one(User.srn == 'PALASH.AGAR@GMAIL.COM')
    t = await Team.find_one()
    p.mentor_team_ids = [str(t.id)]
    await p.save()
    print('Fixed Palash team ids')

if __name__ == '__main__':
    asyncio.run(main())
