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
    await init_beanie(database=client[settings.MONGODB_DB_NAME], document_models=[User])
    
    print(f"Found {len(data)} records in seed_data.json. Syncing...")
    
    for item in data:
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
                encrypted_password=item.get("encrypted_password")
            )
            await user.insert()
            print(f"  [Inserted] {srn}")
        else:
            user.name = item.get("name", user.name)
            user.email = item.get("email", user.email)
            user.role = item.get("role", user.role)
            if "encrypted_password" in item:
                user.encrypted_password = item["encrypted_password"]
            await user.save()
            print(f"  [Updated]  {srn}")
            
    print("Sync complete.")

if __name__ == "__main__":
    asyncio.run(sync())
