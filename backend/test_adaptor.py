import asyncio
from routes.v1.flows import KafkaAdaptor
from services.flow_service import DFV_TOPIC

payload = {
    "event_id": "test",
    "correlation_id": "cor_123",
    "session_id": "6a4d2156d0f21690d8663713",
    "team_id": "TEST_TEAM",
    "student_id": "6a4d1c2d540e2d2e486d8cb3",
    "flow": "dfv",
    "timestamp": "2026-07-07T15:56:10Z",
    "schema_version": "1.0",
    "problem_statement": "Valid 50 char statement.",
    "idea": "Valid idea.",
    "desirability_context": "D" * 105,
    "feasibility_context": "F" * 105,
    "viability_context": "V" * 105
}

async def run():
    print("Testing Adaptor")
    adaptor = KafkaAdaptor()
    try:
        await adaptor.publish(DFV_TOPIC, payload)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(run())
