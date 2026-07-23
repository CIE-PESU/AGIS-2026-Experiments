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
    print('Palash ID:', p.id)
    teams = await Team.find_all().to_list()
    t = teams[0]
    t.mentor_id = str(p.id)
    await t.save()
    print('Reassigned team to Palash')

asyncio.run(main())
