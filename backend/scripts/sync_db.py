import asyncio
import json
import sys
from pathlib import Path

# Add the backend root directory to the python path so we can import from core/models
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.user import User

async def sync():
    seed_file = Path(__file__).parent / "seed_data.json"
    if not seed_file.exists():
        print(f"Error: {seed_file} not found.")
        sys.exit(1)

    try:
        with open(seed_file, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing {seed_file}: {e}")
        sys.exit(1)

    print(f"Connecting to MongoDB at {settings.MONGODB_URI}...")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    print(f"Found {len(data.get('users', []))} users and {len(data.get('teams', []))} teams in seed_data.json. Syncing...")
    
    from models.team import Team
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[User, Team])
    
    # Sync Users
    for item in data.get("users", []):
        srn = item.get("srn")
        if not srn:
            continue
            
        user = await User.find_one(User.srn == srn)
        if not user:
            user = User(
                srn=srn,
                name=item.get("name", srn),
                email=item.get("email"),
                role=item.get("role", "student"),
                encrypted_password=item.get("encrypted_password"),
                team_id=item.get("team_id")
            )
            await user.insert()
            print(f"  [Inserted User] {srn}")
        else:
            user.name = item.get("name", user.name)
            user.email = item.get("email", user.email)
            user.role = item.get("role", user.role)
            user.team_id = item.get("team_id")
            if "encrypted_password" in item:
                user.encrypted_password = item["encrypted_password"]
            await user.save()
            print(f"  [Updated User]  {srn}")

    # Sync Teams (overwrite by ID or name)
    from bson import ObjectId
    for item in data.get("teams", []):
        team_id = item.get("id")
        team = None
        if team_id:
            team = await Team.get(team_id)
            
        if not team:
            # If not found by ID, try by name, or insert new
            team = await Team.find_one(Team.team_name == item.get("team_name"))
            
        if not team:
            # Recreate with the exact same ID if possible
            new_id = ObjectId(team_id) if team_id else None
            team = Team(
                id=new_id,
                team_name=item.get("team_name"),
                mentor_id=item.get("mentor_id"),
                members=item.get("members", [])
            )
            await team.insert()
            print(f"  [Inserted Team] {team.team_name}")
        else:
            team.team_name = item.get("team_name")
            team.mentor_id = item.get("mentor_id")
            team.members = item.get("members", [])
            await team.save()
            print(f"  [Updated Team]  {team.team_name}")
            
    print("Sync complete.")

if __name__ == "__main__":
    asyncio.run(sync())
