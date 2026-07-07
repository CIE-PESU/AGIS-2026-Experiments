import asyncio
from app.database.mongodb import connect_db
from app.models.session import Session
from app.schemas.session import SessionResponse, SessionListResponse

async def run():
    await connect_db()
    session = await Session.find_one({"status": "tipsc_completed"})
    if not session:
        print("No tipsc_completed session found")
        return
    
    print("Found session in DB:", session.id)
    try:
        # test list response
        SessionListResponse.from_document(session)
        print("SessionListResponse OK")
    except Exception as e:
        print("SessionListResponse ERROR:")
        import traceback; traceback.print_exc()

    try:
        # test full response
        SessionResponse.from_document(session)
        print("SessionResponse OK")
    except Exception as e:
        print("SessionResponse ERROR:")
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
