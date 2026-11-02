"""Create a local admin using a prompted password; never writes passwords to disk."""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


async def main():
    from core.security import hash_password
    from database.mongodb import connect_db, disconnect_db
    from models.user import User

    parser = argparse.ArgumentParser()
    parser.add_argument("--srn", default="ADMIN")
    parser.add_argument("--name", default="Administrator")
    args = parser.parse_args()
    password = getpass.getpass("New admin password (8–128 characters): ")
    if not 8 <= len(password) <= 128 or password != getpass.getpass("Confirm password: "):
        raise SystemExit("Password length invalid or confirmation did not match")
    await connect_db()
    try:
        if await User.find_one({"srn": args.srn.upper()}):
            raise SystemExit("Account already exists; no changes made")
        await User(
            srn=args.srn.upper(),
            name=args.name,
            role="admin",
            password_hash=hash_password(password),
        ).insert()
        print("Admin created")
    finally:
        await disconnect_db()


if __name__ == "__main__":
    asyncio.run(main())
