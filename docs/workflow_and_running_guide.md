# Setup, workflow, and operations

All commands below run from the repository root. Supported Python versions are 3.12 and 3.13. Use Node 22.13+ (Node 24 recommended), npm, and a running Docker daemon. Normal operation uses Python directly; `uv` is optional development/dependency tooling.

## Fresh installation

Create one root environment:

```bash
python -m venv .venv
```

Activate it with `source .venv/bin/activate` on macOS/Linux or `.\.venv\Scripts\Activate.ps1` in Windows PowerShell, then install the runtime dependencies:

```bash
python -m pip install -r requirements.txt
python scripts/init_env.py
npm ci --prefix frontend
```

Reactivate this environment whenever you open a new terminal. If you already created it with `uv sync --locked`, activate that same `.venv`; there is no need to recreate it.

`init_env.py` creates `.env` with unique JWT and worker secrets and private file permissions; it refuses to overwrite an existing file. Configure `OPENAI_MODEL_NAME`, `LM_STUDIO_URL`, `OPENAI_API_KEY`, `TAVILY_API_KEY`, and `SERPER_API_KEY`. See [model configuration](model-config.md). The compose stack provides persistent MongoDB on 27017 and Kafka on 9092. These ports must be available; stop conflicting local services or configure different ports consistently.

Start the infrastructure, then provision an administrator once for a fresh database:

```bash
docker compose -f backend/docker-compose.yml up -d --wait
```

```bash
python scripts/bootstrap_admin.py --srn ADMIN --name Administrator
```

This prompts for a password. There is no default password or development authentication bypass. Students authenticate against `PES_AUTH_URL`; locally provisioned admin/mentor accounts use hashed passwords. Use the admin dashboard to manage mentor/team assignments. Clients cannot select a team to grant themselves access at login.

For each normal run, use the activated root environment:

```bash
docker compose -f backend/docker-compose.yml up -d --wait
python dev.py
# Press Ctrl+C when finished, then stop the infrastructure:
docker compose -f backend/docker-compose.yml down
```

`down` preserves MongoDB/Kafka data volumes. The launcher starts the application services; Compose manages MongoDB and Kafka separately.

The launcher waits for actual API and worker readiness, then starts Vite. Any service exit shuts down the remaining process groups. Ctrl+C stops all child services. It binds the API to localhost and deliberately avoids automatic backend reload because reload interrupts in-process TIPSC work.

| Service | Address |
| --- | --- |
| Frontend | http://localhost:5167 |
| API docs | http://localhost:8008/docs |
| Readiness | http://localhost:8008/api/v1/ready |
| Health | http://localhost:8008/api/v1/health |
| Liveness | http://localhost:8008/api/v1/live |
| Worker health, when launched by dev.py | http://localhost:8009/health |

For optional manual operation with the `uv` development environment, use separate terminals:

```bash
uv run --project . --directory backend uvicorn main:app --host 127.0.0.1 --port 8008
uv run --project . --directory backend python -m workers.combined_agent_worker
npm run dev --prefix frontend
```

Without `uv`, activate the root `.venv` in each backend terminal and run `python -m uvicorn main:app --host 127.0.0.1 --port 8008` or `python -m workers.combined_agent_worker` from `backend/`. The notification worker is optional legacy compatibility; current UI polling/SSE reads session updates directly and does not require it.

## Verify changes

These developer checks require the optional `uv` tool and development dependencies (`uv sync --locked`). They are separate from the normal Python start/stop workflow.

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

The audit checker prints documented upstream exceptions and fails on new findings, version changes, or expired reviews. These exceptions do not mean there are zero advisories; see [dependency security](dependency-security.md).

Run deterministic real-infrastructure and browser tests:

```bash
docker compose -p agis-tests -f backend/docker-compose.test.yml up -d --wait
uv run playwright install chromium
AGIS_INTEGRATION=1 uv run pytest -m integration
docker compose -p agis-tests -f backend/docker-compose.test.yml down -v
```

Tests use MongoDB port 27018 by default (`AGIS_TEST_MONGODB_URI` can select an isolated container hostname), Kafka port 19092, unique temporary database names, fake agent outputs, and test-only credentials. Browser tests also use ports 18008 and 15167. Tests never use the development database or make paid LLM calls. Install browser OS libraries with `playwright install --with-deps chromium` on Linux. Without `AGIS_INTEGRATION=1`, integration tests are explicitly skipped.

## Dependencies and API contracts

`pyproject.toml` and `uv.lock` are authoritative. After intentional dependency changes:

```bash
uv lock
uv sync --locked
uv export --locked --no-dev --no-hashes --format requirements-txt --output-file requirements.txt
uv run python backend/scripts/export_openapi.py
uv run python scripts/check_contracts.py
```

`requirements.txt` is a runtime-only, pinned compatibility export for pip users. Developer tools come from the `dev` group (`uv sync` installs it by default). Do not maintain independent platform virtual environments or stale subproject lockfiles. Do not force incompatible major upgrades to silence audit warnings.

## Recovery and deployment boundaries

- TIPSC uses version/run-guarded MongoDB writes. Interrupted running tasks become `tipsc_failed` after the configured timeout and can be retried. Follow-up questions remain parked durably. An API restart does not resume an LLM call from the middle of a stage.
- DFV and Discovery run in isolated, cancellable subprocesses. Completed callbacks are stored in a private SQLite delivery database before HTTP delivery and replayed on Kafka redelivery after restart. Preserve `WORKER_DELIVERY_DB` on the worker host. Keep the consumer-group IDs stable. For a multi-host worker fleet, use durable shared delivery storage before claiming cross-host result reuse.
- Callback outages retain the Kafka offset. Malformed jobs go to a `.dlq` topic before their offsets are committed. A missing or superseded run is terminal; concurrent-version conflicts retry.
- Health/readiness checks require MongoDB, a started Kafka producer, and an initialized TIPSC executor. They do not prove model/search credentials or worker availability. The launcher checks the worker separately.
- Run the supported deployment as one API instance and one combined worker unless you add a shared rate limiter and distributed task/delivery coordination. Current rate-limit buckets are process-local. Place production behind HTTPS and configure explicit CORS origins and frontend API routing.
- Set `VITE_API_BASE_URL` when building a separately hosted frontend, or proxy `/api/v1` to the backend. Vite's development proxy is not a production reverse proxy.
- Existing installations must review [credential and index migrations](dependency-security.md). Account seed exports are disabled by default and never include password fields. Existing `.env` files are not automatically rewritten.

Stop local infrastructure with `docker compose -f backend/docker-compose.yml down`. This preserves data volumes; use `down -v` only when you intend to delete that stack's data.

## Live provider smoke check

`uv run python scripts/provider_smoke.py` sends one short, non-sensitive prompt through the configured CrewAI provider (up to 32 output tokens). It may incur API usage and is intentionally excluded from CI. A successful reply proves basic endpoint/model/credential compatibility, not the quality or tool-calling behavior of an entire agent pipeline.

`uv run python scripts/search_smoke.py` makes one neutral request each to Serper and Tavily using configured credentials. These checks consume provider credits and are excluded from CI.

## Product-Market Fit after Discovery

After a successful Discovery run, open the Product-Market Fit card in the workspace. The existing combined worker also consumes `userSession.pmf`; no separate worker command is needed. PMF receives the founder intake and TIPSC/DFV/Discovery reports. A failed run can be retried, and a completed run can be rerun. Earlier reports remain saved. Survey and retention metrics are marked unmeasured until actual customer evidence is supplied.

See [merge verification](merge-quickstart-pmf.md) for the combined branch checks and remaining upstream dependency findings.

Native Windows instructions and local-model capability checks: [Windows and local LLM operation](windows-local-llm.md). Runtime mock-data fallbacks have been removed; standalone examples require an explicit `--sample` flag.

## Account metadata maintenance

`backend/scripts/seed_data.json` is intentionally empty. Use a private sanitized export rather than committing account records. From the repository root:

```bash
uv run python -m backend.scripts.inspect_db --collection teams --limit 20
uv run python -m backend.scripts.initial_dump
uv run python -m backend.scripts.sync_db --file /private/path/accounts-export.json
# Stop the API/worker and back up the database before applying an import.
uv run python -m backend.scripts.sync_db --file /private/path/accounts-export.json --apply
uv run python -m backend.scripts.migrate_session_teams
```

Export requires `AGIS_EXPORT_PATH` outside the checkout and omits credentials. Import validates stable ObjectIds, normalized SRNs, duplicate records, and team references before writes. Omitted optional fields preserve existing values; imports never overwrite stored passwords. A fresh database restored from metadata needs local passwords provisioned separately. Imports and the session-team migration are maintenance operations, not multi-document transactions: keep writers stopped, retain a backup, and rerun after correcting an interrupted import.

Team members are student SRNs; mentor/team references are ObjectId strings. Use authenticated admin APIs or the dashboard for normal assignment/deletion. Person-specific repair scripts, import-time database mutations, the obsolete live smoke script, and the duplicate backend test tree have been removed. The isolated integration suite is the maintained end-to-end check.
