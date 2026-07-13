import httpx

BASE_URL = "http://localhost:8000/api/v1"
with httpx.Client() as client:
    r = client.post(f"{BASE_URL}/auth/login", json={"srn": "PES1UG24CS115", "password": "testpass"})
    token = r.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # get the latest queued or tipsc_completed session
    r = client.get(f"{BASE_URL}/sessions", headers=headers)
    sessions = r.json()["data"]
    if not sessions:
        print("No sessions")
        exit()
    session_id = sessions[0]["session_id"]
    
    r2 = client.get(f"{BASE_URL}/sessions/{session_id}", headers=headers)
    print(r2.status_code)
    print(r2.text)
