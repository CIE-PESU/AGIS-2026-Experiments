"""
Combined DFV + Customer Discovery agent worker.

Responsibilities:
- Consume userSession.dfv
- Consume userSession.discovery
- Execute the corresponding agent
- Report output (success or failure) to the backend internal API
- Commit Kafka offset (single-shot execution)

Architecture:
    Kafka -> Worker -> Agent -> Internal Backend API -> MongoDB

The worker NEVER writes directly to MongoDB.
The backend remains the single source of truth for state transitions and persistence.
The worker executes each message single-shot without local retries or DLQ requeueing.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import os
import re
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime

# Load .env file for agent environment variables
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from bson import ObjectId
from dotenv import load_dotenv
from pydantic import ValidationError

ENV_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ENV_ROOT / ".env")


# =============================================================================
# PATH BOOTSTRAP
# =============================================================================

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, ".."))

if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


# =============================================================================
# BACKEND IMPORTS
# =============================================================================

from core.config import settings  # noqa: E402 — worker path/environment bootstrap precedes backend imports
from kafka.topics import KafkaTopic  # noqa: E402 — worker path/environment bootstrap precedes backend imports
from models.schema import (  # noqa: E402 — worker path/environment bootstrap precedes backend imports
    DFVJobMessage,
    DiscoveryJobMessage,
)

# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("combined_agent_worker")


def _log(
    correlation_id: str,
    message: str,
    level: str = "info",
) -> None:
    getattr(logger, level)(
        "[correlation=%s] %s",
        correlation_id,
        message,
    )


# =============================================================================
# AGENT MODULE LOADING
# =============================================================================


def _load_module(
    module_name: str,
    file_path: str,
) -> ModuleType:
    """
    Load a Python module directly from an explicit file path.
    """

    module_directory = os.path.dirname(file_path)

    spec = importlib.util.spec_from_file_location(
        module_name,
        file_path,
    )

    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {file_path}")

    module = importlib.util.module_from_spec(spec)

    path_added = False

    if module_directory not in sys.path:
        sys.path.insert(0, module_directory)
        path_added = True

    try:
        spec.loader.exec_module(module)
    finally:
        if path_added:
            sys.path.remove(module_directory)

    return module


def _load_dfv_agent():
    dfv_path = os.path.join(
        PROJECT_ROOT,
        "DFV-agent",
        "main.py",
    )

    try:
        module = _load_module(
            "agis_dfv_agent_main",
            dfv_path,
        )

        logger.info(
            "DFV agent loaded from %s",
            dfv_path,
        )

        return module.run_analysis

    except Exception:
        logger.exception("Failed to load DFV agent")
        raise


def _load_discovery_agent():
    discovery_path = os.path.join(
        PROJECT_ROOT,
        "customer-interview-planner-agent",
        "main.py",
    )

    try:
        module = _load_module(
            "agis_discovery_agent_main",
            discovery_path,
        )

        logger.info(
            "Discovery agent loaded from %s",
            discovery_path,
        )

        return module.run_discovery_analysis

    except Exception:
        logger.exception("Failed to load Discovery agent")
        raise


# =============================================================================
# JSON OUTPUT PARSING
# =============================================================================


def _extract_json_block(raw: str) -> str:
    """
    Remove markdown code fences and stray model text.
    """
    if not raw:
        return ""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE | re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start != -1 and end != -1 and start < end:
            cleaned = cleaned[start : end + 1]

    return cleaned


def _parse_agent_output(result: Any) -> dict[str, Any]:
    """
    Parse CrewAI output into a JSON dictionary.
    """
    pydantic_obj = getattr(result, "validated", None) or getattr(result, "pydantic", None)
    if pydantic_obj and hasattr(pydantic_obj, "model_dump"):
        return pydantic_obj.model_dump(mode="json")

    raw = getattr(result, "raw", result)

    if isinstance(raw, dict):
        return raw

    if not isinstance(raw, str):
        raise ValueError(f"Unexpected agent output type: {type(raw).__name__}")

    cleaned = _extract_json_block(raw)

    logger.info(
        "PARSING AGENT OUTPUT DIAGNOSTICS: repr(raw)=%s, len(raw)=%d, repr(cleaned)=%s, len(cleaned)=%d",
        repr(raw),
        len(raw),
        repr(cleaned),
        len(cleaned),
    )

    if not cleaned or not (cleaned.startswith("{") or cleaned.startswith("[")):
        raise ValueError(
            f"Final Evaluator returned empty or non-JSON output.\n"
            f"repr(raw): {repr(raw)}\n"
            f"len(raw): {len(raw)}\n"
            f"repr(cleaned): {repr(cleaned)}\n"
            f"len(cleaned): {len(cleaned)}\n"
            f"First 200 chars (raw): {repr(raw[:200])}\n"
            f"Last 200 chars (raw): {repr(raw[-200:]) if len(raw) > 200 else repr(raw)}\n"
            f"First 200 chars (cleaned): {repr(cleaned[:200])}\n"
            f"Last 200 chars (cleaned): {repr(cleaned[-200:]) if len(cleaned) > 200 else repr(cleaned)}"
        )

    try:
        parsed = json.loads(cleaned)
    except Exception as exc:
        logger.error("\n===== PARSER FAILURE DIAGNOSTICS =====")
        logger.error("Raw Output (first 200 chars): %s", repr(raw[:200]))
        logger.error(
            "Raw Output (last 200 chars):  %s", repr(raw[-200:]) if len(raw) > 200 else repr(raw)
        )
        logger.error("Cleaned Output (first 200 chars): %s", repr(cleaned[:200]))
        logger.error(
            "Cleaned Output (last 200 chars):  %s",
            repr(cleaned[-200:]) if len(cleaned) > 200 else repr(cleaned),
        )
        logger.error("JSONDecodeError: %s", exc)
        raise exc

    if not isinstance(parsed, dict):
        raise ValueError("Agent output must be a JSON object")

    return parsed


# =============================================================================
# COMBINED WORKER
# =============================================================================


class DeliveryError(RuntimeError):
    """Callback not yet accepted; retain the Kafka offset."""


class CombinedAgentWorker:
    def __init__(self) -> None:

        self.consumer_dfv: AIOKafkaConsumer | None = None

        self.consumer_discovery: AIOKafkaConsumer | None = None

        self.producer: AIOKafkaProducer | None = None

        self.http_client: httpx.AsyncClient | None = None

        # Only ONE agent workload may execute at a time.
        #
        # DFV and Discovery use the same local LLM infrastructure.
        # This prevents simultaneous CrewAI workloads.
        self._agent_lock = asyncio.Lock()
        self._health_server: asyncio.Server | None = None

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    async def start(self) -> None:
        print("START() ENTERED")

        logger.info("Starting Combined Agent Worker")

        consumer_options = {
            "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "security_protocol": settings.KAFKA_SECURITY_PROTOCOL,
            "auto_offset_reset": "earliest",
            "enable_auto_commit": False,
            "value_deserializer": None,
            # Long-running agent workloads.
            "session_timeout_ms": 120_000,
            "heartbeat_interval_ms": 20_000,
            "max_poll_interval_ms": 1_800_000,
            "request_timeout_ms": 60_000,
        }

        # Start consumers with retry logic
        max_retries = 10
        base_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                self.consumer_dfv = AIOKafkaConsumer(
                    KafkaTopic.USER_SESSION_DFV,
                    group_id="combined_agent_worker_group_dfv",
                    **consumer_options,
                )
                await self.consumer_dfv.start()
                print("DFV consumer started")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2**attempt)
                logger.warning(
                    "DFV consumer failed to start (attempt %d/%d): %s. Retrying in %ds...",
                    attempt + 1,
                    max_retries,
                    e,
                    delay,
                )
                await asyncio.sleep(delay)

        for attempt in range(max_retries):
            try:
                self.consumer_discovery = AIOKafkaConsumer(
                    KafkaTopic.USER_SESSION_DISCOVERY,
                    group_id="combined_agent_worker_group_discovery",
                    **consumer_options,
                )
                await self.consumer_discovery.start()
                print("Discovery consumer started")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2**attempt)
                logger.warning(
                    "Discovery consumer failed to start (attempt %d/%d): %s. Retrying in %ds...",
                    attempt + 1,
                    max_retries,
                    e,
                    delay,
                )
                await asyncio.sleep(delay)

        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            security_protocol=settings.KAFKA_SECURITY_PROTOCOL,
        )

        self.http_client = httpx.AsyncClient(
            base_url=settings.WORKER_BACKEND_URL,
            transport=httpx.AsyncHTTPTransport(retries=3),
            timeout=httpx.Timeout(
                connect=10.0,
                read=60.0,
                write=60.0,
                pool=10.0,
            ),
            headers={
                "X-Worker-Secret": settings.WORKER_INTERNAL_SECRET,
            },
        )

        await self.producer.start()
        print("Producer started")

        port = int(os.getenv("WORKER_HEALTH_PORT", "0"))
        if port:

            async def health(reader, writer):
                await reader.read(4096)
                body = b'{"ready":true}'
                writer.write(
                    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
                    + str(len(body)).encode()
                    + b"\r\nConnection: close\r\n\r\n"
                    + body
                )
                await writer.drain()
                writer.close()
                await writer.wait_closed()

            self._health_server = await asyncio.start_server(health, "127.0.0.1", port)

        logger.info(
            "Combined worker started | DFV=%s | Discovery=%s",
            KafkaTopic.USER_SESSION_DFV,
            KafkaTopic.USER_SESSION_DISCOVERY,
        )

    async def stop(self) -> None:

        logger.info("Stopping Combined Agent Worker")

        if self._health_server is not None:
            self._health_server.close()
            await self._health_server.wait_closed()
        if self.consumer_dfv is not None:
            await self.consumer_dfv.stop()

        if self.consumer_discovery is not None:
            await self.consumer_discovery.stop()

        if self.producer is not None:
            await self.producer.stop()

        if self.http_client is not None:
            await self.http_client.aclose()

        logger.info("Combined Agent Worker stopped")

    # =========================================================================
    # INTERNAL BACKEND API
    # =========================================================================

    async def _report_success(
        self,
        *,
        session_id: str,
        correlation_id: str,
        flow: str,
        output: dict[str, Any],
        duration_seconds: float,
    ) -> None:

        if self.http_client is None:
            raise RuntimeError("HTTP client is not initialized")

        await self._deliver_result(
            session_id,
            flow,
            correlation_id,
            "output",
            {
                "correlation_id": correlation_id,
                "flow": flow,
                "output": output,
                "duration_seconds": duration_seconds,
                "worker_id": settings.WORKER_ID,
            },
        )

        _log(
            correlation_id,
            f"{flow.upper()} output accepted by backend",
        )

    async def _report_failure(
        self,
        *,
        session_id: str,
        correlation_id: str,
        flow: str,
        error_code: str,
        error_message: str,
        retry_count: int,
    ) -> None:

        if self.http_client is None:
            raise RuntimeError("HTTP client is not initialized")

        await self._deliver_result(
            session_id,
            flow,
            correlation_id,
            "failure",
            {
                "correlation_id": correlation_id,
                "flow": flow,
                "error_code": error_code,
                "error_message": error_message,
                "retry_count": retry_count,
            },
        )

    @contextmanager
    def _delivery_db(self):
        import sqlite3

        path = Path(
            os.getenv("WORKER_DELIVERY_DB", str(ENV_ROOT / ".local" / "worker-deliveries.sqlite3"))
        )
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        connection = sqlite3.connect(path)
        path.chmod(0o600)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS deliveries (job TEXT PRIMARY KEY, session TEXT, kind TEXT, body TEXT)"
        )
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    async def _deliver_result(self, session_id, flow, correlation_id, kind, body):
        # Persist before HTTP. Redelivery/restart uses this result, without rerunning the agent.
        key = f"{flow}:{correlation_id}"
        with self._delivery_db() as db:
            db.execute(
                "INSERT OR IGNORE INTO deliveries VALUES (?, ?, ?, ?)",
                (key, session_id, kind, json.dumps(body)),
            )
            row = db.execute(
                "SELECT session, kind, body FROM deliveries WHERE job=?", (key,)
            ).fetchone()
        try:
            response = await self.http_client.post(
                f"/internal/sessions/{row[0]}/{row[1]}", json=json.loads(row[2])
            )
            # Missing/superseded runs are terminal: retrying can never apply this result.
            code = response.json().get("error", {}).get("code") if response.is_error else None
            terminal = response.status_code == 404 or (
                response.status_code == 409
                and code in {"CORRELATION_ID_MISMATCH", "INVALID_STATE_TRANSITION"}
            )
            if code == "INVALID_OUTPUT_SCHEMA" and row[1] == "output":
                failure = {
                    "flow": flow,
                    "correlation_id": correlation_id,
                    "error_code": "INVALID_AGENT_OUTPUT",
                    "error_message": "Agent output failed backend schema validation",
                    "retry_count": 0,
                }
                with self._delivery_db() as db:
                    db.execute(
                        "UPDATE deliveries SET kind='failure', body=? WHERE job=?",
                        (json.dumps(failure), key),
                    )
                await self._deliver_result(session_id, flow, correlation_id, "failure", failure)
                return
            if not terminal:
                response.raise_for_status()
        except Exception as exc:
            raise DeliveryError("Persisted callback is awaiting backend acceptance") from exc

    async def _replay_result(self, job, flow):
        with self._delivery_db() as db:
            row = db.execute(
                "SELECT kind, body FROM deliveries WHERE job=?", (f"{flow}:{job.correlation_id}",)
            ).fetchone()
        if row is None:
            return False
        await self._deliver_result(
            job.userSession_id, flow, job.correlation_id, row[0], json.loads(row[1])
        )
        return True

    async def _run_agent(self, flow, inputs):
        import tempfile

        # Both flows share one cancellable process slot. Timeout kills the agent process.
        async with self._agent_lock:
            with tempfile.TemporaryDirectory(prefix="agis-agent-") as directory:
                result_path = Path(directory) / "result.json"
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-m",
                    "workers.agent_runner",
                    flow,
                    str(result_path),
                    cwd=BACKEND_ROOT,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=None,
                )
                try:
                    await asyncio.wait_for(
                        process.communicate(json.dumps(inputs).encode()),
                        settings.AGENT_TIMEOUT_SECONDS,
                    )
                    if process.returncode != 0:
                        raise RuntimeError(
                            "Agent subprocess failed; inspect configured provider and input"
                        )
                    return json.loads(result_path.read_text())
                finally:
                    if process.returncode is None:
                        process.kill()
                        await process.wait()

    # =========================================================================
    # DFV
    # =========================================================================

    async def _process_dfv(
        self,
        job: DFVJobMessage,
    ) -> None:

        started_at = datetime.now(UTC)

        start_time = time.monotonic()

        _log(
            job.correlation_id,
            f"Starting DFV analysis for '{job.idea_name}'",
        )

        dfv_inputs = {
            "desirability": job.payload.desirability_context,
            "feasibility": job.payload.feasibility_context,
            "viability": job.payload.viability_context,
        }
        parsed_output = await self._run_agent("dfv", dfv_inputs)
        completed_at = datetime.now(UTC)

        duration = time.monotonic() - start_time

        dfv_output = {
            "correlation_id": job.correlation_id,
            "status": "done",
            "output": parsed_output,
            "error": None,
            "retry_count": job.retry_count,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "idea_name": job.idea_name,
        }

        await self._report_success(
            session_id=job.userSession_id,
            correlation_id=job.correlation_id,
            flow="dfv",
            output=dfv_output,
            duration_seconds=duration,
        )
        decision = parsed_output.get("final_decision", {}).get("status", "unknown")

        _log(
            job.correlation_id,
            (
                f"DFV completed | "
                f"idea={job.idea_name} | "
                f"decision={decision} | "
                f"duration={duration:.2f}s"
            ),
        )

    # =========================================================================
    # DISCOVERY
    # =========================================================================

    async def _process_discovery(
        self,
        job: DiscoveryJobMessage,
    ) -> None:

        started_at = datetime.now(UTC)

        start_time = time.monotonic()

        _log(
            job.correlation_id,
            "Starting Customer Discovery analysis",
        )

        parsed = await self._run_agent("discovery", job.payload.model_dump())

        completed_at = datetime.now(UTC)

        duration = time.monotonic() - start_time

        discovery_output = {
            "correlation_id": job.correlation_id,
            "status": "done",
            "output": parsed,
            "error": None,
            "retry_count": job.retry_count,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }

        await self._report_success(
            session_id=job.userSession_id,
            correlation_id=job.correlation_id,
            flow="discovery",
            output=discovery_output,
            duration_seconds=duration,
        )

        _log(
            job.correlation_id,
            (f"Customer Discovery completed | duration={duration:.2f}s"),
        )

    # =========================================================================
    # MESSAGE HANDLERS (SINGLE-SHOT EXECUTORS)
    # =========================================================================

    async def _handle_dfv(
        self,
        raw_value: dict[str, Any],
    ) -> None:

        try:
            job = DFVJobMessage(**raw_value)
        except (ValidationError, TypeError) as exc:
            await self._dead_letter(KafkaTopic.USER_SESSION_DFV, raw_value, str(exc))
            return

        if not ObjectId.is_valid(job.userSession_id):
            await self._dead_letter(
                KafkaTopic.USER_SESSION_DFV, raw_value, "Invalid session ObjectId"
            )
            return

        if await self._replay_result(job, "dfv"):
            return
        try:
            await self._process_dfv(job)
        except DeliveryError:
            raise
        except Exception as exc:
            _log(
                job.correlation_id,
                f"DFV failed: {exc}",
                level="error",
            )
            try:
                await self._report_failure(
                    session_id=job.userSession_id,
                    correlation_id=job.correlation_id,
                    flow="dfv",
                    error_code="DFV_AGENT_FAILED",
                    error_message=str(exc),
                    retry_count=job.retry_count,
                )
            except Exception as report_exc:
                raise DeliveryError("Could not deliver failure") from report_exc

    async def _handle_discovery(
        self,
        raw_value: dict[str, Any],
    ) -> None:

        try:
            job = DiscoveryJobMessage(**raw_value)
        except (ValidationError, TypeError) as exc:
            await self._dead_letter(KafkaTopic.USER_SESSION_DISCOVERY, raw_value, str(exc))
            return

        if not ObjectId.is_valid(job.userSession_id):
            await self._dead_letter(
                KafkaTopic.USER_SESSION_DISCOVERY, raw_value, "Invalid session ObjectId"
            )
            return

        if await self._replay_result(job, "discovery"):
            return
        try:
            await self._process_discovery(job)
        except DeliveryError:
            raise
        except Exception as exc:
            _log(
                job.correlation_id,
                f"Discovery failed: {exc}",
                level="error",
            )
            try:
                await self._report_failure(
                    session_id=job.userSession_id,
                    correlation_id=job.correlation_id,
                    flow="discovery",
                    error_code="DISCOVERY_AGENT_FAILED",
                    error_message=str(exc),
                    retry_count=job.retry_count,
                )
            except Exception as report_exc:
                raise DeliveryError("Could not deliver failure") from report_exc

    # =========================================================================
    # CONSUMER LOOPS
    # =========================================================================

    async def _consume_dfv(self) -> None:

        if self.consumer_dfv is None:
            raise RuntimeError("DFV consumer is not initialized")

        await self._consume(self.consumer_dfv, self._handle_dfv)

    async def _consume_discovery(self) -> None:
        if self.consumer_discovery is None:
            raise RuntimeError("Discovery consumer is not initialized")
        await self._consume(self.consumer_discovery, self._handle_discovery)

    async def _dead_letter(self, topic, raw, error):
        if self.producer is None:
            raise DeliveryError("DLQ producer unavailable")
        await self.producer.send_and_wait(
            topic + ".dlq", json.dumps({"payload": raw, "error": error}, default=str).encode()
        )

    async def _consume(self, consumer, handler):
        from aiokafka.structs import TopicPartition

        async def deliver(message):
            while True:
                try:
                    try:
                        raw = (
                            json.loads(message.value)
                            if isinstance(message.value, (bytes, str))
                            else message.value
                        )
                    except (ValueError, UnicodeDecodeError):
                        await self._dead_letter(message.topic, repr(message.value), "Invalid JSON")
                    else:
                        await handler(raw)
                    return
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Message retained; retrying persisted delivery in 5 seconds")
                    await asyncio.sleep(5)

        async for message in consumer:
            partitions = consumer.assignment()
            consumer.pause(*partitions)
            task = asyncio.create_task(deliver(message))
            try:
                # Keep polling while long-running work/callback retries hold the partition.
                # Heartbeats alone do not satisfy max_poll_interval_ms.
                while not task.done():
                    await asyncio.wait({task}, timeout=1)
                    await consumer.getmany(timeout_ms=0)
                await task
                await consumer.commit(
                    {TopicPartition(message.topic, message.partition): message.offset + 1}
                )
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                current = consumer.assignment()
                consumer.resume(*(partition for partition in partitions if partition in current))

    # =========================================================================
    # RUN
    # =========================================================================

    async def run(self) -> None:

        try:
            await self.start()
            await asyncio.gather(
                self._consume_dfv(),
                self._consume_discovery(),
            )

        finally:
            await self.stop()


# =============================================================================
# ENTRY POINT
# =============================================================================


async def main() -> None:
    print("MAIN STARTED")

    worker = CombinedAgentWorker()

    print("RUNNING WORKER")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
