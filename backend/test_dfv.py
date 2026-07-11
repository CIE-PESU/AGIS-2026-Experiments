import asyncio
from database.mongodb import connect_db
from services.flow_service import FlowService
from repositories.session_repo import session_repo
from kafka.producer import kafka_producer
from services.audit_service import audit_service
from models.session import Session

async def run():
    await connect_db()
    session = await Session.find_one({"status": "tipsc_completed"})
    if not session:
        print("No tipsc_completed session")
        return
        
    class KafkaAdaptor:
        async def publish(self, topic, payload):
            print("Kafka mock publish")
            return "ok"
    
    flow_service = FlowService(
        session_repo=session_repo,
        kafka_producer=KafkaAdaptor(),
        audit_service=audit_service
    )
    
    try:
        await flow_service.trigger_dfv(
            str(session.id),
            session.student_id,
            {"desirability_context": "D"*100, "feasibility_context": "F"*100, "viability_context": "V"*100}
        )
        print("Success")
    except Exception as e:
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
