# AGIS backend

Run from the repository root with `uv sync --locked` and `uv run python dev.py`. See [setup](../docs/workflow_and_running_guide.md), [backend architecture](../docs/backend-arch.md), and [dependency security](../docs/dependency-security.md).

The active application is `backend/main.py`; from `backend/`, use `uv run --project .. uvicorn main:app --host 127.0.0.1 --port 8008`. The duplicate `backend/app/` implementation has been removed.

Create an initial administrator with `uv run python scripts/bootstrap_admin.py`. The password is prompted and stored as a salted scrypt hash. There are no built-in passwords and no development authentication bypass.

Do not share Fernet keys or commit account exports. `backend/scripts/seed_data.json` is an empty fixture. Optional sanitized exports require an explicit private `AGIS_EXPORT_PATH` outside the repository.
