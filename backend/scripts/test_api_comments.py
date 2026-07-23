import asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from core.config import settings

async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First login as student
        response = await ac.post("/api/v1/auth/login", json={
            "srn": "PES1UG24AM371",
            "password": "password"
        })
        token = response.json().get("access_token")
        print("Login:", response.status_code)
        
        # Get active session
        response = await ac.get("/api/v1/sessions/user/PES1UG24AM371/session", headers={"Authorization": f"Bearer {token}"})
        print("Session:", response.status_code)
        if response.status_code != 200:
            print(response.text)
            return
            
        session_id = response.json()["data"]["id"]
        print("Session ID:", session_id)
        
        # Get comments
        response = await ac.get(f"/api/v1/sessions/{session_id}/comments", headers={"Authorization": f"Bearer {token}"})
        print("Comments:", response.status_code)
        print(response.json())

if __name__ == '__main__':
    asyncio.run(main())
