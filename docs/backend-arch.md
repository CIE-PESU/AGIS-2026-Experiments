# Backend architecture

The active FastAPI application is `backend/main.py`. There is one backend implementation. Configuration comes from root `.env`/environment through `core/config.py`; dependency resolution comes from root `pyproject.toml` and `uv.lock`.

## Components

- `routes/v1/`: authenticated public API mounted at `/api/v1`.
- `routes/internal/`: worker callbacks under `/internal`, protected by a shared worker secret.
- `services/`: authentication, authorization-aware session orchestration, flow handling, audit, and workspace lifecycle.
- `repositories/` and `models/`: Beanie/Motor persistence with indexes, versions, and conditional updates.
- `state_machine/`: backend session statuses and legal transitions.
- `events/`: MongoDB/Kafka/TIPSC startup and graceful task/connection shutdown.
- `workers/combined_agent_worker.py`: consumes DFV/Discovery jobs, runs isolated agents, persists delivery results, and invokes authenticated callbacks.
- `TIPSC-Agent/src/engine/`: direct asynchronous TIPSC executor and task-local guarded session store.

## Request and execution flow

Session creation validates intake, scopes the idempotency key to the authenticated owner, and creates a single active session. Unique partial indexes prevent simultaneous creations for the same owner. It queues and starts TIPSC in-process. TIPSC performs PreEval, concurrent validation/regulatory checks, Ethics, compliance-context assembly, and TIPSC scoring. It either fails, completes, or parks one founder question. Follow-up submission atomically claims the current version/turn before scheduling reevaluation.

DFV requires TIPSC's `ready_for_dfv`. Discovery is blocked after a NO-GO DFV decision. These flows atomically store a correlation ID, start time, input, and optional idempotency record, then publish a validated Kafka job. The worker reports an output or failure through the internal API; the backend validates the schema, correlation ID, state transition, and version before writing.

Idempotency records are scoped to owner/session and flow. Reusing a key with a different body is a conflict. Replay responses retain the original run identity. Ownership checks precede all replay responses.

## Concurrency and failure semantics

MongoDB updates for worker failure/timeout require the expected version and run ID; allowed active states are checked in the write predicate. Pipeline writes are scoped to the current task's correlation ID/version and cannot overwrite an archived, completed, or superseded run. Every accepted pipeline update increments the version.

The timeout supervisor makes abandoned TIPSC, DFV, and Discovery work explicitly retryable. TIPSC is recoverable by retry after timeout, not by resuming a partially completed model call. Shutdown cancels and awaits registered pipeline tasks before disconnecting the database.

The worker serializes both agent types through one process slot. It terminates an agent process on timeout/cancellation. A SQLite mailbox stores the callback before HTTP; restart/redelivery reuses the saved result. Kafka offsets are committed only after callback acceptance or durable dead-letter publication. The worker retries transient callback failures and version conflicts. Missing/superseded runs are terminal. Persist the mailbox volume; cross-host mailbox sharing is not implemented.

## Authentication and data isolation

PES credentials are validated by the external service; there is no password or environment bypass. Local accounts use scrypt hashes. Legacy encrypted passwords migrate at successful login using the existing private Fernet key. Refresh tokens are high-entropy random values stored as indexed SHA-256 digests and consumed atomically. Student refresh preserves workspace claims. Mentors access supervised teams; admin routes enforce roles, and mentor roster reads are scoped.

Magic links issue `mentor_workspace` tokens. Every protected workspace request checks active/revoked status. SSE uses the same Authorization header and ownership logic as ordinary requests and rechecks token expiry/revocation while streaming. Revocation denies access before background session/comment/token cleanup; audit records remain.

## Operational boundaries

Readiness checks actual MongoDB, Kafka-producer, and TIPSC-executor state. Liveness only proves the API can respond. Request limits count actual streamed bytes. Rate limits are process-local; use the documented single-instance deployment or add a shared limiter before scaling. Configure private delivery/cache directories and production TLS/CORS. See [running guide](workflow_and_running_guide.md) and [security/migrations](dependency-security.md).

The canonical request schemas are in `backend/schemas`, Kafka models in `backend/models/schema.py`, persisted session schema in `docs/schema.json`, and generated API specification in `docs/api-spec-generated.json`.
