import httpx
import uuid
import sys

with httpx.Client() as client:
    # login
    r = client.post("http://localhost:8000/api/v1/auth/login", json={"srn": "PES1UG24CS115", "password": "testpass"})
    token = r.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # get session
    # let's just get the one we just created
    session_id = "6a4d1dcb644a87f14e331bc2"
    r = client.get(f"http://localhost:8000/api/v1/sessions/{session_id}", headers=headers)
    print(r.status_code)
    print(r.json())
