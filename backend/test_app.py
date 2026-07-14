import uuid
from fastapi.testclient import TestClient
from main import app
import os
from dotenv import load_dotenv

load_dotenv()

with TestClient(app) as client:
    # Login
    r = client.post("/api/v1/auth/login", json={"srn": "PES1UG24CS115", "password": "testpass"})
    token = r.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Cleanup
    r_list = client.get("/api/v1/sessions", headers=headers)
    for s in r_list.json().get("data", []):
        client.delete(f"/api/v1/sessions/{s['session_id']}", headers=headers)

    # Create Session
    session_payload = {
        "team_id": "TEST_TEAM",
        "problem_statement": "This is a completely valid fifty character long problem statement designed to pass the new B-21 edge case rules.",
        "idea": "An AI agent that automatically writes integration smoke tests."
    }
    r2 = client.post("/api/v1/sessions", headers={**headers, "Idempotency-Key": str(uuid.uuid4())}, json=session_payload)
    session_id = r2.json()["data"]["session_id"]
    correlation_id = r2.json()["data"]["correlation_id"]

    # Trigger Worker Output for TIPSC
    WORKER_SECRET = os.environ.get("WORKER_INTERNAL_SECRET", "super_secret_worker_token_2026")
    tipsc_output = {
        "correlation_id": correlation_id,
        "flow": "tipsc",
        "duration_seconds": 2.5,
        "worker_id": "test_worker_bot",
        "output": {
            "score": {"timing": 4, "idea": 3, "problem": 5, "solution": 4, "competition": 2},
            "total_score": 18,
            "ready_for_dfv": True,
            "compliance_flag": False,
            "compliance_issues": [],
            "followups_asked": 0,
            "reasoning": "The idea is highly structured and feasible."
        }
    }
    r3 = client.post(f"/internal/sessions/{session_id}/output", headers={"X-Worker-Secret": WORKER_SECRET}, json=tipsc_output)

    # Trigger DFV
    dfv_payload = {
        "desirability_context": "D" * 105,
        "feasibility_context": "F" * 105,
        "viability_context": "V" * 105
    }
    try:
        r4 = client.post(f"/api/v1/sessions/{session_id}/trigger/dfv", headers=headers, json=dfv_payload)
        print("DFV Trigger Status:", r4.status_code)
        print(r4.text)
    except Exception as e:
        import traceback
        traceback.print_exc()

