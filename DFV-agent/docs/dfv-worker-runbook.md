# DFV Worker Runbook

Local setup + operating guide for the DFV consumer and notification worker.
For the message schema and retry matrix, see `dfv-worker-contract.md`.

## Prerequisites

- Kafka running locally in KRaft mode, broker at `127.0.0.1:9092`
- MongoDB running locally at `127.0.0.1:27017` (Compass optional, for inspection)
- LM Studio running with the model loaded, serving at `http://127.0.0.1:1234/v1`
- Python deps installed: `uv add aiokafka motor kafka-python`

## One-time setup

Create the required topics (safe to re-run, skips existing ones):
```
uv run python -u -m kafka_scripts.create_topics
```
Creates: `userSession.dfv`, `userSession.dfv.dlq`, `userSession.notifications`

## Starting the workers

Two independent workers, run in separate terminals from `DFV-agent/`:

**DFV consumer** (processes jobs, writes results to Mongo, publishes completion events):
```
uv run python -u -m workers.dfv_consumer
```

**Notification worker** (turns completion events into a polling-ready signal):
```
uv run python -u -m workers.notification_worker
```

Both use `-m` (module syntax), not a direct file path — running as `python workers/dfv_consumer.py`
fails with `ModuleNotFoundError: No module named 'models'` because Python doesn't add the
project root to its search path that way.

## Publishing a test job

```
uv run python -u -m kafka_scripts.dfv_producer
```
Publishes Google Glass, SNACCED, and Blinkit with fake session IDs — useful for local testing
without waiting on backend's real trigger endpoint.

## Verifying it worked

**Check Kafka directly** (from the Kafka install folder):
```
.\bin\windows\kafka-console-consumer.bat --bootstrap-server 127.0.0.1:9092 --topic userSession.notifications --from-beginning
```

**Check Mongo** (Compass): look in `agis.userSessions` for a document with:
- `dfv.status` → should reach `"done"`
- `notifications.dfv` → polling-ready signal, `seen: false`
- `notificationLog` → audit trail array

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'models'` | Ran with `python workers/dfv_consumer.py` instead of module syntax | Use `python -m workers.dfv_consumer` |
| `ModuleNotFoundError: No module named 'kafka'` after renaming folders | Installed into `uv`'s venv but ran with global `python` | Prefix every command with `uv run` |
| Consumer hangs indefinitely on startup, no error | `listeners`/`advertised.listeners` mismatch in `server.properties` (e.g. one says `localhost`, other says `127.0.0.1`) | Use `127.0.0.1` consistently in both; restart broker |
| `ImportError: cannot import name 'run_analysis' from 'main'`, but a full CrewAI run printed first | `main.py`'s crew execution code isn't wrapped in a function — running at import time instead of being defined as `run_analysis()` | Wrap the crew/kickoff block in `def run_analysis(inputs): ...` and gate the test block behind `if __name__ == "__main__":` |
| `WARNING: Consumer poll timeout has expired` / `CommitFailedError` | CrewAI run took longer than Kafka's `max_poll_interval_ms` (5 min default), consumer got kicked from the group | Expected occasionally with long-running analyses; the idempotency check prevents duplicate reprocessing when this happens |
| Worker restarts and reprocesses a job that already finished | Should not happen — idempotency check queries Mongo for `dfv.status == "done"` before running. If it does happen, check `_already_done()` is matching on the right `correlation_id` | See `tests/test_idempotency.py` to reproduce and debug |

## Restarting after a crash

Both workers are safe to just restart — `enable_auto_commit=False` combined with the idempotency
check means a mid-job crash results in, at worst, a redone analysis for that one job (not corrupted
data or duplicate DB writes). No manual cleanup needed.

## Killing a stuck worker

`CTRL+C` in its terminal. If it doesn't respond (rare), close the terminal window — Kafka will
detect the dropped connection via heartbeat timeout and rebalance the partition to any other
running consumer in the same group within a few minutes.
