import json
import os
from pathlib import Path
from models.user import User
from models.team import Team

def get_seed_file_path() -> Path:
    return Path(__file__).resolve().parent.parent / "scripts" / "seed_data.json"

async def dump_seed_data():
    """
    Dumps all users and teams from the database into scripts/seed_data.json.
    This allows the file to be committed to git and stay in sync with admin actions.
    """
    users = await User.find_all().to_list()
    teams = await Team.find_all().to_list()

    data = {
        "users": [],
        "teams": []
    }

    for u in users:
        u_dict = u.model_dump()
        u_dict["id"] = str(u.id)
        if u_dict.get("team_id"):
            u_dict["team_id"] = str(u_dict["team_id"])
        data["users"].append(u_dict)

    for t in teams:
        t_dict = t.model_dump()
        t_dict["id"] = str(t.id)
        data["teams"].append(t_dict)

    seed_file = get_seed_file_path()
    
    # Write to a temporary file first to prevent corruption if interrupted
    tmp_file = seed_file.with_suffix(".json.tmp")
    with open(tmp_file, "w") as f:
        json.dump(data, f, indent=2, default=str)
    
    os.replace(tmp_file, seed_file)
