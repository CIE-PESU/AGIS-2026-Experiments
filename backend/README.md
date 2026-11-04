# AGIS backend

From the repository root, activate `.venv`, run `docker compose -f backend/docker-compose.yml up -d --wait`, then `python dev.py`. After Ctrl+C, run `docker compose -f backend/docker-compose.yml down` to stop infrastructure while preserving data. Install the complete locked runtime export once with `python -m pip install --no-deps -r requirements.txt`, or use `uv sync --locked --no-dev` to apply the project's dependency override. See [setup](../docs/workflow_and_running_guide.md), [backend architecture](../docs/backend-arch.md), and [dependency security](../docs/dependency-security.md).

The active application is `backend/main.py`; from `backend/` with the root environment activated, use `python -m uvicorn main:app --host 127.0.0.1 --port 8008`. The duplicate `backend/app/` implementation has been removed.

Backend startup provisions nine shared student, mentor, and admin accounts with salted scrypt hashes. See the [root README](../README.md) for logins. `python scripts/bootstrap_admin.py` remains available to create an additional administrator with a prompted password. Authentication is enforced for all accounts.

Do not share Fernet keys or commit account exports. `backend/scripts/seed_data.json` is an empty fixture. Optional sanitized exports require an explicit private `AGIS_EXPORT_PATH` outside the repository.

Metadata inspection/import/export commands and their validation rules are documented in the [maintenance guide](../docs/workflow_and_running_guide.md#account-metadata-maintenance). Use the admin API for team and mentor edits. Tests live under root `tests/`.
