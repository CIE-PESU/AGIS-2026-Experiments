import json
import os
from pathlib import Path

from core.config import settings
from models.team import Team
from models.user import User


def get_seed_file_path() -> Path:
    if settings.AGIS_EXPORT_PATH is None:
        raise ValueError("AGIS_EXPORT_PATH is not configured")
    return settings.AGIS_EXPORT_PATH.expanduser()


async def dump_seed_data():
    """
    Optionally export account/team metadata without password material.
    Disabled unless AGIS_EXPORT_PATH points to a private location outside the repo.
    """
    if settings.AGIS_EXPORT_PATH is None:
        return
    users = await User.find_all().to_list()
    teams = await Team.find_all().to_list()

    data = {"users": [], "teams": []}

    for u in users:
        u_dict = u.model_dump(exclude={"password_hash", "encrypted_password"})
        u_dict["id"] = str(u.id)
        if u_dict.get("team_id"):
            u_dict["team_id"] = str(u_dict["team_id"])
        data["users"].append(u_dict)

    for t in teams:
        t_dict = t.model_dump()
        t_dict["id"] = str(t.id)
        data["teams"].append(t_dict)

    seed_file = get_seed_file_path().resolve()
    repository = Path(__file__).resolve().parents[2]
    if seed_file.is_relative_to(repository):
        raise ValueError("AGIS_EXPORT_PATH must be outside the repository")

    # Write to a temporary file first to prevent corruption if interrupted
    import uuid

    seed_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = seed_file.with_suffix(f".{uuid.uuid4().hex}.tmp")
    with tmp_file.open("x") as f:
        tmp_file.chmod(0o600)
        json.dump(data, f, indent=2, default=str)

    os.replace(tmp_file, seed_file)
