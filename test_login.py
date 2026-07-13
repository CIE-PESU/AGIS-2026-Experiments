import asyncio
from app.services.auth_service import auth_service
from app.database.mongodb import connect_db

async def run():
    await connect_db()
    try:
        res = await auth_service.login("PES1UG24CS115", "test")
        print(res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
