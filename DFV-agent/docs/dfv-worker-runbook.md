# Combined worker operations

The active worker is `backend/workers/combined_agent_worker.py`, which consumes `userSession.dfv` and `userSession.discovery`. It launches one cancellable agent subprocess at a time and posts callbacks to `/internal/sessions/{id}/output` or `/failure` with `X-Worker-Secret`.

Run from the repository root:

```bash
uv run --project . --directory backend python -m workers.combined_agent_worker
```

Or use `uv run python dev.py` to supervise the API, worker, and frontend together. Configure `WORKER_BACKEND_URL`, `WORKER_INTERNAL_SECRET`, Kafka settings, and provider keys in the root environment. Set `WORKER_HEALTH_PORT` to enable a local readiness endpoint after connections initialize.

Callbacks are written to `WORKER_DELIVERY_DB` (default `.local/worker-deliveries.sqlite3`) before delivery. Preserve this private file across process restarts. Transient callback failures retry without committing the message or rerunning a saved result. Completed deliveries remain available for deduplication; plan retention/archival based on your Kafka replay horizon and protect the file as application data. Multiple hosts need shared durable result storage before guaranteeing cross-host reuse.

Malformed payloads are published to the corresponding `.dlq` topic before commit. Monitor and inspect DLQ messages using appropriate access controls. This worker does not automatically requeue failed agent runs; users retry with revised inputs/new run IDs. A timeout kills the local agent process. Remote provider cancellation/billing depends on the provider.

See [full operations](../../docs/workflow_and_running_guide.md), [contracts](../../docs/flow-shapes.md), and [dependency risks](../../docs/dependency-security.md). The old `workers.dfv_consumer` entry point is no longer part of this project.
