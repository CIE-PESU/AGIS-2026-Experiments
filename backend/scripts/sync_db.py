import asyncio
import argparse
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

async def sync(replace_staff=False):
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

    print("Connecting to configured MongoDB...")
    client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    print(f"Found {len(data.get('users', []))} users and {len(data.get('teams', []))} teams in seed_data.json. Syncing...")
    
    from models.team import Team
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[User, Team])
    
    # Sync Users
    for item in data.get("users", []):
        srn = item.get("srn")
        if not srn:
            continue
            
        user = await User.find_one(User.srn == srn)
        is_staff = item.get("role") in ("admin", "mentor")
        # Rename seeded staff in place so their team references remain valid.
        if not user and replace_staff and is_staff and item.get("id"):
            candidate = await User.get(item["id"])
            if candidate and candidate.role in ("admin", "mentor"):
                user = candidate
        if not user:
            from bson import ObjectId
            user = User(
                id=ObjectId(item["id"]) if is_staff and item.get("id") else None,
                srn=srn,
                name=item.get("name", srn),
                email=item.get("email"),
                role=item.get("role", "student"),
                encrypted_password=item.get("encrypted_password"),
                team_id=item.get("team_id"),
                mentor_team_ids=item.get("mentor_team_ids", [])
            )
            await user.insert()
            print(f"  [Inserted User] {srn}")
        else:
            user.srn = srn
            user.name = item.get("name", user.name)
            user.email = item.get("email", user.email)
            user.role = item.get("role", user.role)
            user.team_id = item.get("team_id")
            user.mentor_team_ids = item.get("mentor_team_ids", [])
            if "encrypted_password" in item:
                user.encrypted_password = item["encrypted_password"]
            await user.save()
            print(f"  [Updated User]  {srn}")

    if replace_staff:
        staff_srns = [u["srn"] for u in data.get("users", [])
                      if u.get("role") in ("admin", "mentor")]
        await User.find({"role": {"$in": ["admin", "mentor"]},
                         "srn": {"$nin": staff_srns}}).delete()
        mentors = await User.find(User.role == "mentor").to_list()
        mentor_refs = [ref for u in mentors for ref in (str(u.id), u.srn)]
        await Team.find({"mentor_id": {"$nin": mentor_refs}}).update(
            {"$set": {"mentor_id": ""}}
        )
        print("Removed staff absent from seed and cleared stale mentor assignments.")

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
    client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synchronize seeded users and teams.")
    parser.add_argument("--replace-staff", action="store_true",
                        help="Remove admins and mentors not present in the seed file.")
    args = parser.parse_args()
    asyncio.run(sync(replace_staff=args.replace_staff))
