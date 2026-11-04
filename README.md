# AGIS entrepreneurship platform

A React application and FastAPI backend for Quickstart evaluation, Ethics/TIPSC assessment, DFV analysis, customer-discovery planning, and Product-Market Fit analysis. MongoDB stores sessions; Kafka dispatches DFV, Discovery, and PMF jobs. TIPSC runs asynchronously in the API process with guarded persistence and timeout recovery.

## Start locally

Use Python 3.12 or 3.13, Node 22.13+ (Node 24 recommended), and Docker Compose.

One-time setup from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --no-deps -r requirements.txt
python scripts/init_env.py
# Edit .env: set the LLM endpoint/model/API key and search API keys.
npm ci --prefix frontend
```

On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1` instead of `source .venv/bin/activate`. Activate the same environment whenever you open a new terminal.

The requirements export contains all locked runtime dependencies. `--no-deps` preserves the reviewed Filelock override that LiteLLM's dependency metadata otherwise rejects. Alternatively, use `uv sync --locked --no-dev`, which applies the override directly. See [dependency security](docs/dependency-security.md).

For each run, from the repository root with the environment activated:

```bash
docker compose -f backend/docker-compose.yml up -d --wait
python dev.py
# Press Ctrl+C to stop the application, then stop MongoDB and Kafka:
docker compose -f backend/docker-compose.yml down
```

Backend startup automatically creates this branch's six shared accounts when they are missing. Existing accounts, passwords, and team assignments are preserved. `down` preserves database volumes.

| Username (SRN field) | Password | Role |
| --- | --- | --- |
| admin1 | aerodactyl1 | Admin |
| admin2 | aerodactyl2 | Admin |
| admin3 | aerodactyl3 | Admin |
| mentor1 | mosasaur1 | Mentor |
| mentor2 | mosasaur2 | Mentor |
| mentor3 | mosasaur3 | Mentor |

The bundled password hashes live in `backend/scripts/branch_accounts.json`. These shared logins are available to everyone with this branch.

Open `http://localhost:5167`. API docs: `http://localhost:8008/docs`. Readiness: `http://localhost:8008/api/v1/ready`. PES logins require the configured PES authentication service.

## Verify

The checks below use the optional `uv` development tooling. Install the locked development environment with `uv sync --locked` first; `uv` is not required for the normal start/stop commands above.

```bash
uv run ruff check .
uv run ruff format --check .
uv run python scripts/check_repository.py
uv run mypy backend
uv run pytest -m 'not integration'
npm test --prefix frontend
npm run build --prefix frontend
uv run python scripts/check_contracts.py
uv run python scripts/audit_dependencies.py
npm audit --prefix frontend
```

For real MongoDB/Kafka and browser tests, see the [running guide](docs/workflow_and_running_guide.md). Dependency versions are maintained in root `pyproject.toml` and `uv.lock`; `requirements.txt` is a generated runtime export. Agent manifests describe their standalone packages, but all platform commands use the root environment.

- [Repository audit](docs/repository-audit.md)
- [Setup and operations](docs/workflow_and_running_guide.md)
- [Backend](docs/backend-arch.md) and [frontend](docs/frontend-arch.md) architecture
- [API and contracts](docs/api-spec.md)
- [Roles and permissions](docs/rbac.md)
- [Model configuration](docs/model-config.md)
- [Known upstream dependency risks and migration notes](docs/dependency-security.md)

For native Windows and local-model setup, process ownership, and data-integrity safeguards, see [Windows and local LLM operation](docs/windows-local-llm.md).
