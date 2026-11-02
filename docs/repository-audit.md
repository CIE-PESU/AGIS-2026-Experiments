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
