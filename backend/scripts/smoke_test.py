import os
import sys
import time
import uuid
from getpass import getpass

try:
    import httpx
    from dotenv import load_dotenv
except ImportError:
    print("❌ Missing dependencies. Please run: pip install httpx python-dotenv")
    sys.exit(1)

# Load backend/.env file to get the WORKER_INTERNAL_SECRET
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE_URL = "http://localhost:8000/api/v1"
INTERNAL_URL = "http://localhost:8000/internal"

WORKER_SECRET = os.getenv("WORKER_INTERNAL_SECRET")
if not WORKER_SECRET:
    print("❌ WORKER_INTERNAL_SECRET not found. Make sure backend/.env is populated.")
    sys.exit(1)

def run_smoke_test():
    print("\n" + "="*50)
    print(" AGIS Backend: B-19 Integration Smoke Test")
    print("="*50 + "\n")
    
    print("This script will run the full 10-step happy path for a session lifecycle.")
    print("Please ensure your local server is running (uvicorn app.main:app).\n")
    
    # Hardcoded dummy credentials for automated testing
    srn = "PES1UG24CS115"
    password = "testpass"

    with httpx.Client() as client:
        # Step 1: Login
        print("\n[Step 1/10] Logging in...")
        resp = client.post(f"{BASE_URL}/auth/login", json={"srn": srn, "password": password})
        if resp.status_code != 200:
            print(f"❌ Login failed! HTTP {resp.status_code}")
            print(resp.text)
            sys.exit(1)
            
        token = resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful. Acquired JWT token.")

        # Step 1.5: Clean up any existing active sessions (from previous failed runs)
        print("\n[Step 1.5/10] Cleaning up any existing sessions...")
        list_resp = client.get(f"{BASE_URL}/sessions", headers=headers)
        if list_resp.status_code == 200:
            for s in list_resp.json()["data"]:
                if s["status"] != "archived":
                    client.delete(f"{BASE_URL}/sessions/{s['session_id']}", headers=headers)
                    print(f"   Archived left-over session: {s['session_id']}")

        # Step 2: Create Session
        print("\n[Step 2/10] Creating Session...")
        idempotency_key = str(uuid.uuid4())
        session_payload = {
            "team_id": "TEST_TEAM",
            "problem_statement": "This is a completely valid fifty character long problem statement designed to pass the new B-21 edge case rules.",
            "idea": "An AI agent that automatically writes integration smoke tests."
        }
        
        resp = client.post(
            f"{BASE_URL}/sessions", 
            headers={**headers, "Idempotency-Key": idempotency_key}, 
            json=session_payload
        )
        if resp.status_code != 201:
            print(f"❌ Session creation failed! HTTP {resp.status_code}")
            print(resp.text)
            sys.exit(1)
            
        resp_json = resp.json()
        print("DEBUG CREATE SESSION RESP:", resp_json)
        
        session_id = resp_json["data"]["session_id"]
        status = resp_json["data"]["status"]
        print(f"✅ Session created: {session_id} (Status: {status})")

        # Give Kafka / async tasks a split second to fire
        time.sleep(1)

        # Re-fetch session to get the correlation ID needed for the worker API
        resp = client.get(f"{BASE_URL}/sessions/{session_id}", headers=headers)
        correlation_id = resp.json()["data"]["correlation_id"]

        # Step 3: Simulate TIPSC Worker Output
        print("\n[Step 3/10] Simulating TIPSC Worker Output...")
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
        resp = client.post(
            f"{INTERNAL_URL}/sessions/{session_id}/output",
            headers={"X-Worker-Secret": WORKER_SECRET},
            json=tipsc_output
        )
        if resp.status_code != 200:
            print(f"❌ Worker output failed: {resp.text}")
            sys.exit(1)
        print("✅ TIPSC Worker output accepted.")

        # Step 4: Poll Session
        print("\n[Step 4/10] Polling session status...")
        resp = client.get(f"{BASE_URL}/sessions/{session_id}", headers=headers)
        status = resp.json()["data"]["status"]
        print(f"   Current status: {status}")
        if status != "tipsc_completed":
            print("❌ Expected tipsc_completed!")
            sys.exit(1)
        print("✅ Status correctly advanced to tipsc_completed.")

        # Step 5: Trigger DFV
        print("\n[Step 5/10] Triggering DFV flow...")
        dfv_payload = {
            "desirability_context": "D" * 105,
            "feasibility_context": "F" * 105,
            "viability_context": "V" * 105
        }
        resp = client.post(f"{BASE_URL}/sessions/{session_id}/trigger/dfv", headers=headers, json=dfv_payload)
        if resp.status_code != 200:
            print(f"❌ DFV trigger failed! HTTP {resp.status_code}\n{resp.text}")
            sys.exit(1)
            
        resp_json = resp.json()
        payload = resp_json.get("data", resp_json)
        status = payload.get("status")
        correlation_id = payload.get("correlation_id")
        print(f"✅ DFV triggered. Status is now: {status}")

        # Step 6: Simulate DFV output
        print("\n[Step 6/10] Simulating DFV Worker Output...")
        dfv_output = {
            "correlation_id": correlation_id,
            "flow": "dfv",
            "duration_seconds": 3.2,
            "worker_id": "test_worker_bot",
            "output": {
                "desirability": {"score": 5, "report": "High demand.", "recommendations": []},
                "feasibility": {"score": 4, "report": "Technically viable.", "recommendations": []},
                "viability": {"score": 4, "report": "Good market.", "recommendations": []},
                "overall_decision": "GO",
                "summary": "Proceed to discovery phase.",
                "json_report": {}
            }
        }
        resp = client.post(
            f"{INTERNAL_URL}/sessions/{session_id}/output",
            headers={"X-Worker-Secret": WORKER_SECRET},
            json=dfv_output
        )
        if resp.status_code != 200:
            print(f"❌ Worker output failed: {resp.text}")
            sys.exit(1)
        print("✅ DFV Worker output accepted.")

        # Step 7: Trigger Discovery
        print("\n[Step 7/10] Triggering Discovery flow...")
        resp = client.post(f"{BASE_URL}/sessions/{session_id}/trigger/discovery", headers=headers)
        if resp.status_code != 200:
            print(f"❌ Discovery trigger failed! HTTP {resp.status_code}\n{resp.text}")
            sys.exit(1)
            
        resp_json = resp.json()
        payload = resp_json.get("data", resp_json)
        status = payload.get("status")
        correlation_id = payload.get("correlation_id")
        print(f"✅ Discovery triggered. Status is now: {status}")

        # Step 8: Simulate Discovery output
        print("\n[Step 8/10] Simulating Discovery Worker Output...")
        discovery_output = {
            "correlation_id": correlation_id,
            "flow": "discovery",
            "duration_seconds": 4.1,
            "worker_id": "test_worker_bot",
            "output": {
                "jtbd_elements": [{"job": "Testing software", "outcome": "Success", "pain": "Manual effort"}],
                "interview_plan": {
                    "target_segment": "Software Engineers", 
                    "interview_questions": ["What is hard about testing?"], 
                    "hypothesis_to_validate": "Engineers want automation."
                }
            }
        }
        resp = client.post(
            f"{INTERNAL_URL}/sessions/{session_id}/output",
            headers={"X-Worker-Secret": WORKER_SECRET},
            json=discovery_output
        )
        if resp.status_code != 200:
            print(f"❌ Worker output failed: {resp.text}")
            sys.exit(1)
        print("✅ Discovery Worker output accepted.")

        # Step 9: Confirm COMPLETED
        print("\n[Step 9/10] Confirming final COMPLETED state...")
        resp = client.get(f"{BASE_URL}/sessions/{session_id}", headers=headers)
        status = resp.json()["data"]["status"]
        print(f"   Final Session Status: {status}")
        if status != "completed":
            print("❌ Expected status to be 'completed'!")
            sys.exit(1)
        print("✅ Session successfully reached COMPLETED state.")

        # Step 10: Get History
        print("\n[Step 10/10] Fetching Audit History...")
        resp = client.get(f"{BASE_URL}/sessions/{session_id}/history", headers=headers)
        resp_json = resp.json()
        print("DEBUG HISTORY RESP:", resp_json)
        history = resp_json.get("data", resp_json)
        
        print(f"✅ Found {len(history)} audit events. Timeline:")
        for idx, event in enumerate(reversed(history), 1):
            actor_type = event.get('actor_role', 'worker')
            print(f"   {idx}. {event['event']} (by {actor_type})")
            
        if len(history) < 9:
            print(f"⚠️ Warning: Expected at least 9 events, but found {len(history)}.")
        else:
            print("\n🎉 SMOKE TEST PASSED END-TO-END! 🎉")

if __name__ == "__main__":
    run_smoke_test()
