from datetime import datetime
import uuid
from kafka.payloads import DFVEventPayload

payload = {
    "event_id": str(uuid.uuid4()),
    "correlation_id": "cor_123",
    "session_id": "6a4d2156d0f21690d8663713",
    "team_id": "TEST_TEAM",
    "student_id": "6a4d1c2d540e2d2e486d8cb3",
    "flow": "dfv",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "schema_version": "1.0",
    "problem_statement": "Valid 50 char statement.",
    "idea": "Valid idea.",
    "desirability_context": "D" * 105,
    "feasibility_context": "F" * 105,
    "viability_context": "V" * 105
}

try:
    DFVEventPayload(**payload)
    print("Validation passed!")
except Exception as e:
    print("VALIDATION ERROR:")
    print(e)
