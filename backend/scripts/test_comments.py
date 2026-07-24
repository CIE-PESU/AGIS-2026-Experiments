import asyncio
from core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.comment import MentorComment

async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[MentorComment])
    comments = await MentorComment.find_all().to_list()
    print('Comments count:', len(comments))
    for c in comments:
        print(f"[{c.session_id}] {c.comment}")

if __name__ == '__main__':
    asyncio.run(main())
