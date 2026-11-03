# Repository audit — 2 November 2026

This audit fixes verified defects and establishes repeatable checks; it does not prove the absence of every possible runtime failure.

## Repairs

- Centralized frontend stage/running-state helpers, removed unused imports/state, enabled unused-variable checks, and corrected roster rating casing/activity metadata.
- Restored identity from the backend when display cache is absent, cleared stale active-session IDs, guarded late session responses, and prevented old refresh responses from overwriting a new login or restoring logged-out credentials.
- Validated team member SRNs, mentor references, duplicate members, and conflicting membership before edits. Serialized team mutations within the supported single-API deployment. Corrected mentor member lookup and team ID serialization.
- Resolved mentor authorization against current assignments on each request. Mentor deletion unassigns teams, revokes refresh tokens and linked workspaces, and invalidates mentor access. Workspace lists retain the mentor association.
- Reworked seed imports to retain stable account/team IDs, reject conflicting identities, preserve omitted associations and stored credentials, and validate references before writes. Export temporary files are cleaned up after failure. Session-team migration handles unassigned students without replacing entire session documents.
- Removed person-specific database repair scripts, redundant comment/Kafka test scripts, unused idempotency helpers, and the obsolete live smoke script. Root tests and the documented maintenance commands replace them.
- Removed global SDK monkey patches from DFV and Quickstart, consolidated Quickstart output parsing, corrected optional research-tool handling, and made worker timestamps UTC-aware. Terminal missing-session callbacks no longer retry forever when a proxy returns HTML.
- Extended Python lint/format checks to agents, scripts, tests, and notebooks. Added repository syntax, structured-data duplicate-key, and local documentation-link checks. Updated setup, API, RBAC, model, worker, frontend, and maintenance documentation.

## Verification

Verified locally on macOS with Python 3.13:

- 786 unit tests and 22 real MongoDB/Kafka/browser integration tests passed.
- 13 frontend tests and the production TypeScript/Vite build passed.
- Repository-wide Ruff lint/format, mypy for 121 backend files, generated API/schema checks, and Git whitespace checks passed.
- Syntax, structured-data, and local documentation-link checks passed for 278 tracked/new files.
- The runtime requirements export exactly matches the locked manifest. npm audit found zero advisories; the Python checker passed with the four existing reviewed exceptions.

Upstream CrewAI and Beanie/lazy-model deprecation warnings remain visible; they are not suppressed. Windows and Python 3.12 were not executed during this local audit.

Run the commands in [setup and operations](workflow_and_running_guide.md#verify-changes). Automated integration tests use isolated MongoDB/Kafka and deterministic agent outputs. Local HTTP tests check CrewAI against a test-only OpenAI-compatible server. Production credentials, data, and external providers are not exercised.

Python advisory auditing still reports the four reviewed ChromaDB 1.5.9 exceptions in [dependency security](dependency-security.md). The npm audit reports no advisories. Provider-specific inference, native Windows execution, and CI-host behavior require those environments; a passing local suite does not substitute for them.

## Runtime follow-up — 3 November 2026

Fixed the development launcher's routing so persisted worker callbacks and frontend requests reach the API it actually starts. The launcher supplies `WORKER_BACKEND_URL`, `VITE_BACKEND_URL`, and `VITE_API_BASE_URL`; stale shell or environment-file addresses cannot redirect these services. Manual Vite startup now reads frontend `.env` and mode-specific files for its proxy target. Local `.env` worker/CORS ports were also corrected; that private file is not tracked by Git.

The supported local ports are frontend **5167**, API **8008**, worker health **8009**, MongoDB **27017**, and Kafka **9092**. Isolated tests use MongoDB **27018**, Kafka **19092**, browser API **18008**, and browser frontend **15167**. The model endpoint has its own configured address; the platform does not start a model server.

Fixed a false occupied-port error on immediate POSIX restarts by matching asyncio's address-reuse behavior for sockets in `TIME_WAIT`. Active listeners are still rejected, and Windows retains its existing bind behavior. Added real-socket regression coverage. Invalid application settings now fail before starting child services and report field names without printing credential values. An inherited `DEBUG=WARN` was rejected during verification; boolean shell overrides must be corrected or removed.

Corrected fresh-install instructions: the complete locked requirements export requires `pip install --no-deps -r requirements.txt`, or use `uv sync --locked --no-dev`. Ordinary pip resolution was reproduced failing on LiteLLM's stale Filelock upper bound. No package version or advisory exception was changed.

Verified on macOS with Python 3.13 and Node 26:

- **852** Python tests and **22** isolated MongoDB/Kafka/browser integration tests passed. The browser journey covers TIPSC, DFV, Discovery, and PMF, including reload persistence, alongside login, refresh/logout, and workspace access checks.
- **18** frontend tests and the production TypeScript/Vite build passed.
- Ruff lint/format, backend mypy, repository syntax/data/documentation checks, generated API/schema checks, and whitespace checks passed. The runtime requirements export matches the lockfile apart from the export command's output filename in its generated header.
- Two real `dev.py` launches with deliberately stale worker/frontend addresses passed API/worker/frontend readiness, proxy instance checks, frontend API-base checks, persisted callback replay over HTTP with Kafka offset commit, graceful shutdown, and immediate restart. This used an isolated temporary database and a test-only callback for a missing session; no agent inference was needed for this check.
- A small live CrewAI request succeeded against the configured model, and neutral authenticated Serper and Tavily searches succeeded. These are connectivity/credential smoke checks, not a full live inference evaluation.
- npm audit reported zero vulnerabilities. The Python advisory checker passed with the same four documented ChromaDB exceptions.

Full pipeline integration uses deterministic agent outputs. Native Windows execution, a live PES student authentication exchange, and a complete multi-stage run against live model/search providers were not exercised here. Upstream deprecation warnings and the documented ChromaDB risks remain.
