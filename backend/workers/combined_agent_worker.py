"""
Combined DFV + Customer Discovery agent worker.

Responsibilities:
- Consume userSession.dfv
- Consume userSession.discovery
- Execute the corresponding agent
- Report successful output to the backend internal API
- Retry failed jobs through Kafka
- Send exhausted jobs to DLQ
- Report final failures to the backend

Architecture:
    Kafka -> Worker -> Agent -> Internal Backend API -> MongoDB

The worker NEVER writes directly to MongoDB.
The backend remains the source of truth for state transitions and persistence.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from types import ModuleType
from typing import Any

import httpx
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import ValidationError


# =============================================================================
# PATH BOOTSTRAP
# =============================================================================

BACKEND_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

PROJECT_ROOT = os.path.abspath(
    os.path.join(BACKEND_ROOT, "..")
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
    DeadLetterMessage,
    DiscoveryDeadLetterMessage,
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

def _clear_conflicting_modules() -> None:
    """
    Agent projects contain their own `models` packages.

    Clear cached agent model modules before loading another project to avoid
    Python resolving `models.schema` from the wrong project.
    """

    for module_name in list(sys.modules):
        if module_name == "models" or module_name.startswith("models."):
            del sys.modules[module_name]


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
        raise ImportError(
            f"Unable to load module from {file_path}"
        )

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
        logger.exception(
            "Failed to load DFV agent"
        )
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
        logger.exception(
            "Failed to load Discovery agent"
        )
        raise


# Load agents before restoring backend models.

run_dfv_analysis = _load_dfv_agent()

_clear_conflicting_modules()

# Restore backend root as highest priority.
if BACKEND_ROOT in sys.path:
    sys.path.remove(BACKEND_ROOT)

sys.path.insert(0, BACKEND_ROOT)

run_discovery_analysis = _load_discovery_agent()

_clear_conflicting_modules()

if BACKEND_ROOT in sys.path:
    sys.path.remove(BACKEND_ROOT)

sys.path.insert(0, BACKEND_ROOT)


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

    logger.info("PARSING AGENT OUTPUT DIAGNOSTICS: repr(raw)=%s, len(raw)=%d, repr(cleaned)=%s, len(cleaned)=%d", repr(raw), len(raw), repr(cleaned), len(cleaned))

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

        self.producer: AIOKafkaProducer | None = None

        self.http_client: httpx.AsyncClient | None = None

        # Only ONE agent workload may execute at a time.
        #
        # DFV and Discovery use the same local LLM infrastructure.
        # This prevents simultaneous CrewAI workloads.
        self._agent_lock = asyncio.Lock()


    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    async def start(self) -> None:
        print("START() ENTERED")

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

        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        )

        self.http_client = httpx.AsyncClient(
            base_url=settings.WORKER_BACKEND_URL,
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
        print("DFV consumer started")

        await self.consumer_discovery.start()
        print("Discovery consumer started")
        await self.producer.start()
        print("Producer started")

        logger.info(
            "Combined worker started | DFV=%s | Discovery=%s",
            KafkaTopic.USER_SESSION_DFV,
            KafkaTopic.USER_SESSION_DISCOVERY,
        )


    async def stop(self) -> None:

        logger.info(
            "Stopping Combined Agent Worker"
        )

        if self.consumer_dfv is not None:
            await self.consumer_dfv.stop()

        if self.consumer_discovery is not None:
            await self.consumer_discovery.stop()

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

            logger.error(
                "Backend rejected failure report "
                "[status=%s] %s",
                response.status_code,
                response.text,
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
            print(">>> STARTING DFV ANALYSIS")
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    run_dfv_analysis,
                    dfv_inputs,
                ),
                timeout=settings.AGENT_TIMEOUT_SECONDS,
            )
        parsed_output = _parse_agent_output(result)
        print("Completed DFV")
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
        print("4")
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

        result = await asyncio.wait_for(
            asyncio.to_thread(
                run_discovery_analysis,
                job.payload.model_dump(),
            ),
            timeout=settings.AGENT_TIMEOUT_SECONDS,
        )

        raw_output = getattr(result, "raw", str(result))

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
    # RETRIES
    # =========================================================================

    async def _retry_dfv(
        self,
        job: DFVJobMessage,
    ) -> None:

        if self.producer is None:
            raise RuntimeError(
                "Kafka producer is not initialized"
            )

        await self.producer.send_and_wait(
            KafkaTopic.USER_SESSION_DFV,
            value=job.model_dump_json().encode("utf-8"),
            key=job.userSession_id.encode("utf-8"),
        )


    async def _retry_discovery(
        self,
        job: DiscoveryJobMessage,
    ) -> None:

        if self.producer is None:
            raise RuntimeError(
                "Kafka producer is not initialized"
            )

        await self.producer.send_and_wait(
            KafkaTopic.USER_SESSION_DISCOVERY,
            value=job.model_dump_json().encode("utf-8"),
            key=job.userSession_id.encode("utf-8"),
        )


    # =========================================================================
    # DLQ
    # =========================================================================

    async def _send_dfv_dlq(
        self,
        job: DFVJobMessage,
        reason: str,
    ) -> None:

        if self.producer is None:
            raise RuntimeError(
                "Kafka producer is not initialized"
            )

        message = DeadLetterMessage(
            original_message=job,
            failure_reason=reason,
        )

        await self.producer.send_and_wait(
            KafkaTopic.USER_SESSION_DFV_DLQ,
            value=message.model_dump_json().encode("utf-8"),
            key=job.userSession_id.encode("utf-8"),
        )


    async def _send_discovery_dlq(
        self,
        job: DiscoveryJobMessage,
        reason: str,
    ) -> None:

        if self.producer is None:
            raise RuntimeError(
                "Kafka producer is not initialized"
            )

        message = DiscoveryDeadLetterMessage(
            original_message=job,
            failure_reason=reason,
        )

        await self.producer.send_and_wait(
            KafkaTopic.USER_SESSION_DISCOVERY_DLQ,
            value=message.model_dump_json().encode("utf-8"),
            key=job.userSession_id.encode("utf-8"),
        )


    # =========================================================================
    # MESSAGE HANDLERS
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

            job.retry_count += 1

            _log(
                job.correlation_id,
                f"DFV failed: {exc}",
                level="error",
            )

            if job.retry_count <= settings.AGENT_MAX_RETRIES:

                _log(
                    job.correlation_id,
                    (
                        f"Requeueing DFV "
                        f"retry={job.retry_count}/"
                        f"{settings.AGENT_MAX_RETRIES}"
                    ),
                    level="warning",
                )

                await self._retry_dfv(job)

                return

            await self._send_dfv_dlq(
                job,
                str(exc),
            )

            await self._report_failure(
                session_id=job.userSession_id,
                correlation_id=job.correlation_id,
                flow="dfv",
                error_code="DFV_AGENT_FAILED",
                error_message=str(exc),
                retry_count=job.retry_count,
            )


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

            job.retry_count += 1

            _log(
                job.correlation_id,
                f"Discovery failed: {exc}",
                level="error",
            )

            if job.retry_count <= settings.AGENT_MAX_RETRIES:

                _log(
                    job.correlation_id,
                    (
                        "Requeueing Discovery "
                        f"retry={job.retry_count}/"
                        f"{settings.AGENT_MAX_RETRIES}"
                    ),
                    level="warning",
                )

                await self._retry_discovery(job)

                return

            await self._send_discovery_dlq(
                job,
                str(exc),
            )

            await self._report_failure(
                session_id=job.userSession_id,
                correlation_id=job.correlation_id,
                flow="discovery",
                error_code="DISCOVERY_AGENT_FAILED",
                error_message=str(exc),
                retry_count=job.retry_count,
            )


    # =========================================================================
    # CONSUMER LOOPS
    # =========================================================================

    async def _consume_dfv(self) -> None:

        if self.consumer_dfv is None:
            raise RuntimeError(
                "DFV consumer is not initialized"
            )

        async for message in self.consumer_dfv:
            print("RECEIVED DFV MESSAGE")
            print(message.value)
            try:

                await self._handle_dfv(
                    message.value
                )

                await self.consumer_dfv.commit()

            except Exception:

                logger.exception(
                    "Unexpected DFV consumer error"
                )


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

                await self.consumer_discovery.commit()

            except Exception:

                logger.exception(
                    "Unexpected Discovery consumer error"
                )


    # =========================================================================
    # RUN
    # =========================================================================

    async def run(self) -> None:

        await self.start()

        try:

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