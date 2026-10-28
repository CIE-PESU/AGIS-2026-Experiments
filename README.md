# AGIS entrepreneurship platform

A React application and FastAPI backend for Quickstart evaluation, Ethics/TIPSC assessment, DFV analysis, and customer-discovery planning. MongoDB stores sessions; Kafka dispatches DFV and Discovery jobs. TIPSC runs asynchronously in the API process with guarded persistence and timeout recovery.

## Start locally

Use Python 3.12 or 3.13, Node 22.13+ (Node 24 recommended), uv, and Docker Compose.

```bash
uv sync --locked
python3 scripts/init_env.py
# Edit .env: set the LLM endpoint/model/API key and search API keys.
npm ci --prefix frontend
docker compose -f backend/docker-compose.yml up -d --wait
uv run python scripts/bootstrap_admin.py
uv run python dev.py
```

Open `http://localhost:5167`. API docs: `http://localhost:8008/docs`. Readiness: `http://localhost:8008/api/v1/ready`. PES logins require the configured PES authentication service. Local admin/mentor passwords must be provisioned; no default credentials are shipped.

## Verify

```bash
uv run ruff check backend
uv run ruff format --check backend
uv run mypy backend
uv run pytest -m 'not integration'
npm test --prefix frontend
npm run build --prefix frontend
uv run python scripts/check_contracts.py
uv run python scripts/audit_dependencies.py
npm audit --prefix frontend
```

For real MongoDB/Kafka and browser tests, see the [running guide](docs/workflow_and_running_guide.md). Dependency versions are maintained in root `pyproject.toml` and `uv.lock`; `requirements.txt` is a generated runtime export. Agent manifests describe their standalone packages, but all platform commands use the root environment.

- [Setup and operations](docs/workflow_and_running_guide.md)
- [Backend](docs/backend-arch.md) and [frontend](docs/frontend-arch.md) architecture
- [API and contracts](docs/api-spec.md)
- [Roles and permissions](docs/rbac.md)
- [Model configuration](docs/model-config.md)
- [Known upstream dependency risks and migration notes](docs/dependency-security.md)
