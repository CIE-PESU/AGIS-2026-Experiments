import asyncio
from database.mongodb import connect_db
from services.worker_service import worker_service
from fastapi import BackgroundTasks

async def run():
    await connect_db()
    try:
        # I need to get the correlation_id of the session created
        from models.session import Session
        session = await Session.find_one({"status": "queued"})
        if not session:
            print("No queued session")
            return
            
        tipsc_output = {
            "score": {"timing": 4, "idea": 3, "problem": 5, "solution": 4, "competition": 2},
            "total_score": 18,
            "ready_for_dfv": True,
            "compliance_flag": False,
            "compliance_issues": [],
            "followups_asked": 0,
            "reasoning": "The idea is highly structured and feasible."
        }
        
        bg_tasks = BackgroundTasks()
        await worker_service.accept_flow_output(
            session_id=str(session.id),
            flow="tipsc",
            correlation_id=session.correlation_id,
            output=tipsc_output,
            duration_seconds=2.5,
            worker_id="test_worker_bot",
            background_tasks=bg_tasks,
        )
        print("Success")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
