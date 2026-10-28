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

import os, sys
from pathlib import Path
_local_appdata = Path(__file__).resolve().parent.parent.parent / '.crewai_storage'
_local_appdata.mkdir(parents=True, exist_ok=True)
os.environ['LOCALAPPDATA'] = str(_local_appdata)

import asyncio
import json
import logging
import os
import sys
import time
import tempfile
import signal
from datetime import datetime, timezone
from typing import Any
import re
import httpx
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import ValidationError


# =============================================================================
# PATH BOOTSTRAP
# =============================================================================

BACKEND_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


# =============================================================================
# BACKEND IMPORTS
# =============================================================================

from core.config import settings
from kafka.topics import KafkaTopic
from models.schema import (
    DFVJobMessage,
    DiscoveryJobMessage,
    PMFJobMessage,
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


# Agent execution is isolated in workers.agent_runner.

async def _run_agent_subprocess(flow: str, payload: dict[str, Any]) -> Any:
    """Kill the agent process on timeout so no timed-out job keeps running."""
    with tempfile.TemporaryDirectory(prefix=f"agis-{flow}-") as directory:
        result_path = os.path.join(directory, "result.json")
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "workers.agent_runner", flow, result_path,
            cwd=BACKEND_ROOT,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=os.name != "nt",
        )
        try:
            _, stderr = await asyncio.wait_for(
                process.communicate(json.dumps(payload).encode("utf-8")),
                timeout=settings.AGENT_TIMEOUT_SECONDS,
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            if process.returncode is None:
                if os.name == "nt":
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                await process.wait()
            raise
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace")[-1000:].strip()
            raise RuntimeError(f"{flow} agent exited with code {process.returncode}: {detail}")
        with open(result_path, encoding="utf-8") as result_file:
            return json.load(result_file)


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
            cleaned = cleaned[start:end + 1]

    return cleaned


def _parse_agent_output(result: Any) -> dict[str, Any]:
    """
    Parse CrewAI output into a JSON dictionary.
    """
    pydantic_obj = getattr(result, "validated", None) or getattr(result, "pydantic", None)
    if pydantic_obj and hasattr(pydantic_obj, "model_dump"):
        return pydantic_obj.model_dump()

    raw = getattr(result, "raw", result)

    if isinstance(raw, dict):
        return raw

    if not isinstance(raw, str):
        raise ValueError(
            f"Unexpected agent output type: {type(raw).__name__}"
        )

    cleaned = _extract_json_block(raw)

    logger.debug("Parsing agent output: raw_length=%d cleaned_length=%d", len(raw), len(cleaned))

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
        logger.error("Raw Output (last 200 chars):  %s", repr(raw[-200:]) if len(raw) > 200 else repr(raw))
        logger.error("Cleaned Output (first 200 chars): %s", repr(cleaned[:200]))
        logger.error("Cleaned Output (last 200 chars):  %s", repr(cleaned[-200:]) if len(cleaned) > 200 else repr(cleaned))
        logger.error("JSONDecodeError: %s", exc)
        raise exc

    if not isinstance(parsed, dict):
        raise ValueError(
            "Agent output must be a JSON object"
        )

    return parsed


# =============================================================================
# COMBINED WORKER
# =============================================================================

class CombinedAgentWorker:

    def __init__(self) -> None:

        self.consumer_dfv: AIOKafkaConsumer | None = None

        self.consumer_discovery: AIOKafkaConsumer | None = None

        self.consumer_pmf: AIOKafkaConsumer | None = None

        self.producer: AIOKafkaProducer | None = None

        self.http_client: httpx.AsyncClient | None = None

        # Only ONE agent workload may execute at a time.
        self._agent_lock = asyncio.Lock()


    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    async def start(self) -> None:

        logger.info(
            "Starting Combined Agent Worker"
        )

        consumer_options = {
            "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "auto_offset_reset": "earliest",
            "enable_auto_commit": False,
            "value_deserializer": lambda value: json.loads(
                value.decode("utf-8")
            ),

            # Long-running agent workloads.
            "session_timeout_ms": 120_000,
            "heartbeat_interval_ms": 20_000,
            "max_poll_interval_ms": 1_800_000,
        }

        self.consumer_dfv = AIOKafkaConsumer(
            KafkaTopic.USER_SESSION_DFV,
            group_id="combined_agent_worker_group_dfv",
            **consumer_options,
        )

        self.consumer_discovery = AIOKafkaConsumer(
            KafkaTopic.USER_SESSION_DISCOVERY,
            group_id="combined_agent_worker_group_discovery",
            **consumer_options,
        )

        self.consumer_pmf = AIOKafkaConsumer(
            KafkaTopic.USER_SESSION_PMF,
            group_id="combined_agent_worker_group_pmf",
            **consumer_options,
        )

        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
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

        await self.consumer_dfv.start()

        await self.consumer_discovery.start()

        await self.consumer_pmf.start()
        await self.producer.start()

        logger.info(
            "Combined worker started | DFV=%s | Discovery=%s | PMF=%s",
            KafkaTopic.USER_SESSION_DFV,
            KafkaTopic.USER_SESSION_DISCOVERY,
            KafkaTopic.USER_SESSION_PMF,
        )
        ready_file = os.environ.get("AGIS_WORKER_READY_FILE")
        if ready_file:
            Path(ready_file).write_text("ready", encoding="utf-8")


    async def stop(self) -> None:

        ready_file = os.environ.get("AGIS_WORKER_READY_FILE")
        if ready_file:
            Path(ready_file).unlink(missing_ok=True)

        logger.info(
            "Stopping Combined Agent Worker"
        )

        if self.consumer_dfv is not None:
            await self.consumer_dfv.stop()

        if self.consumer_discovery is not None:
            await self.consumer_discovery.stop()

        if self.consumer_pmf is not None:
            await self.consumer_pmf.stop()

        if self.producer is not None:
            await self.producer.stop()

        if self.http_client is not None:
            await self.http_client.aclose()

        logger.info(
            "Combined Agent Worker stopped"
        )


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
            raise RuntimeError(
                "HTTP client is not initialized"
            )

        response = await self.http_client.post(
            f"/internal/sessions/{session_id}/output",
            json={
                "correlation_id": correlation_id,
                "flow": flow,
                "output": output,
                "duration_seconds": duration_seconds,
                "worker_id": settings.WORKER_ID,
            },
        )

        if response.is_error:

            if response.status_code in (404, 409):
                _log(correlation_id, f"Ignoring stale {flow} output callback", level="warning")
                return

            raise RuntimeError(
                "Backend rejected worker output "
                f"[status={response.status_code}] "
                f"{response.text}"
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
            raise RuntimeError(
                "HTTP client is not initialized"
            )

        response = await self.http_client.post(
            f"/internal/sessions/{session_id}/failure",
            json={
                "correlation_id": correlation_id,
                "flow": flow,
                "error_code": error_code,
                "error_message": error_message,
                "retry_count": retry_count,
            },
        )

        if response.is_error:
            if response.status_code in (404, 409):
                _log(correlation_id, f"Ignoring stale {flow} failure callback", level="warning")
                return
            raise RuntimeError(
                f"Backend rejected {flow} failure report "
                f"[status={response.status_code}] {response.text}"
            )


    # =========================================================================
    # DFV
    # =========================================================================

    async def _process_dfv(
        self,
        job: DFVJobMessage,
    ) -> None:

        started_at = datetime.now(timezone.utc)

        start_time = time.monotonic()

        _log(
            job.correlation_id,
            f"Starting DFV analysis for '{job.idea_name}'",
        )
        

        async with self._agent_lock:
            dfv_inputs = {
                "desirability": job.payload.desirability_context,
                "feasibility": job.payload.feasibility_context,
                "viability": job.payload.viability_context,
            }
            result = await _run_agent_subprocess("dfv", dfv_inputs)
        parsed_output = _parse_agent_output(result)
        completed_at = datetime.now(timezone.utc)

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
        decision = (
            parsed_output
            .get("final_decision", {})
            .get("status", "unknown")
        )

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

        started_at = datetime.now(timezone.utc)

        start_time = time.monotonic()

        _log(
            job.correlation_id,
            "Starting Customer Discovery analysis",
        )

        async with self._agent_lock:
            result = await _run_agent_subprocess("discovery", job.payload.model_dump())

        raw_output = result if isinstance(result, str) else json.dumps(result)

        parsed = {
            "report": raw_output
        }

        completed_at = datetime.now(timezone.utc)

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
            (
                "Customer Discovery completed | "
                f"duration={duration:.2f}s"
            ),
        )


    # =========================================================================
    # PMF
    # =========================================================================

    async def _process_pmf(
        self,
        job: PMFJobMessage,
    ) -> None:

        started_at = datetime.now(timezone.utc)
        start_time = time.monotonic()

        _log(
            job.correlation_id,
            "Starting Product-Market Fit analysis",
        )

        async with self._agent_lock:
            result = await _run_agent_subprocess("pmf", job.payload.model_dump())

        parsed = _parse_agent_output(result)
        completed_at = datetime.now(timezone.utc)
        duration = time.monotonic() - start_time

        pmf_output = {
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
            flow="pmf",
            output=pmf_output,
            duration_seconds=duration,
        )

        _log(
            job.correlation_id,
            f"Product-Market Fit completed | duration={duration:.2f}s",
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
        except ValidationError as exc:
            logger.error(
                "Malformed DFV Kafka message: %s",
                exc,
            )
            return

        try:
            await self._process_dfv(job)
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
                logger.error(
                    "Failed to report DFV failure to backend: %s",
                    report_exc,
                )
                raise


    async def _handle_discovery(
        self,
        raw_value: dict[str, Any],
    ) -> None:

        try:
            job = DiscoveryJobMessage(**raw_value)
        except ValidationError as exc:
            logger.error(
                "Malformed Discovery Kafka message: %s",
                exc,
            )
            return

        try:
            await self._process_discovery(job)
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
                logger.error(
                    "Failed to report Discovery failure to backend: %s",
                    report_exc,
                )
                raise


    async def _handle_pmf(
        self,
        raw_value: dict[str, Any],
    ) -> None:

        try:
            job = PMFJobMessage(**raw_value)
        except ValidationError as exc:
            logger.error(
                "Malformed PMF Kafka message: %s",
                exc,
            )
            return

        try:
            await self._process_pmf(job)
        except Exception as exc:
            _log(
                job.correlation_id,
                f"PMF failed: {exc}",
                level="error",
            )
            try:
                await self._report_failure(
                    session_id=job.userSession_id,
                    correlation_id=job.correlation_id,
                    flow="pmf",
                    error_code="PMF_AGENT_FAILED",
                    error_message=str(exc),
                    retry_count=job.retry_count,
                )
            except Exception as report_exc:
                logger.error(
                    "Failed to report PMF failure to backend: %s",
                    report_exc,
                )
                raise


    # =========================================================================
    # CONSUMER LOOPS
    # =========================================================================

    async def _consume_dfv(self) -> None:

        if self.consumer_dfv is None:
            raise RuntimeError(
                "DFV consumer is not initialized"
            )

        async for message in self.consumer_dfv:
            try:
                await self._handle_dfv(
                    message.value
                )
            except Exception:
                logger.exception(
                    "Unexpected DFV consumer error"
                )
                raise
            await self.consumer_dfv.commit()


    async def _consume_discovery(self) -> None:

        if self.consumer_discovery is None:
            raise RuntimeError(
                "Discovery consumer is not initialized"
            )

        async for message in self.consumer_discovery:
            try:
                await self._handle_discovery(
                    message.value
                )
            except Exception:
                logger.exception(
                    "Unexpected Discovery consumer error"
                )
                raise
            await self.consumer_discovery.commit()


    async def _consume_pmf(self) -> None:

        if self.consumer_pmf is None:
            raise RuntimeError(
                "PMF consumer is not initialized"
            )

        async for message in self.consumer_pmf:
            try:
                await self._handle_pmf(
                    message.value
                )
            except Exception:
                logger.exception(
                    "Unexpected PMF consumer error"
                )
                raise
            await self.consumer_pmf.commit()


    # =========================================================================
    # RUN
    # =========================================================================

    async def run(self) -> None:
        try:
            await self.start()
            await asyncio.gather(
                self._consume_dfv(),
                self._consume_discovery(),
                self._consume_pmf(),
            )

        finally:
            await self.stop()


# =============================================================================
# ENTRY POINT
# =============================================================================

async def main() -> None:
    worker = CombinedAgentWorker()
    await worker.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(main())
