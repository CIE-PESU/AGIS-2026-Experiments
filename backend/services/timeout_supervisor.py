"""
services/timeout_supervisor.py

Lightweight background supervisor that detects sessions stuck in waiting or running
states (e.g. DFV_WAITING, DISCOVERY_WAITING) past a configurable timeout window
and transitions them to failure states (DFV_FAILED, DISCOVERY_FAILED).

Does NOT re-trigger agents, issue Kafka retries, or use DLQs.
Allows normal frontend user retries to start new runs with fresh correlation IDs.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from beanie.operators import In

from core.config import settings
from models.session import Session
from repositories.session_repo import session_repo
from services.audit_service import audit_service
from state_machine.states import SessionStatus

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    """MongoDB may return UTC timestamps without timezone information."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class TimeoutSupervisor:
    """Background supervisor for recovering timed-out flow sessions."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False

    async def check_and_recover_stuck_sessions(
        self,
        timeout_seconds: int = 1800,
    ) -> dict[str, int]:
        """
        Scan for sessions stuck in waiting or running state longer than timeout_seconds
        and transition them to DFV_FAILED / DISCOVERY_FAILED.
        """
        now = _utc_now()
        recovered_counts = {"dfv": 0, "discovery": 0, "pmf": 0}

        for flow, waiting, running, failed, label in (
            (
                "dfv",
                SessionStatus.DFV_WAITING,
                SessionStatus.DFV_RUNNING,
                SessionStatus.DFV_FAILED,
                "DFV",
            ),
            (
                "discovery",
                SessionStatus.DISCOVERY_WAITING,
                SessionStatus.DISCOVERY_RUNNING,
                SessionStatus.DISCOVERY_FAILED,
                "Discovery",
            ),
            (
                "pmf",
                SessionStatus.PMF_WAITING,
                SessionStatus.PMF_RUNNING,
                SessionStatus.PMF_FAILED,
                "PMF",
            ),
        ):
            try:
                sessions = await Session.find(
                    In("status", [waiting.value, running.value])
                ).to_list()
            except Exception:
                logger.exception("Timeout supervisor could not scan %s sessions", flow)
                continue
            for session in sessions:
                try:
                    start_time = session.flow_started_at or session.updated_at
                    if not start_time or now - _as_utc(start_time) < timedelta(
                        seconds=timeout_seconds
                    ):
                        continue
                    session_id = str(session.id)
                    # Match both the run and version so a late timeout cannot overwrite completion.
                    updated = await session_repo.update_flow_failure(
                        session_id=session_id,
                        new_status=failed,
                        expected_version=session.version,
                        correlation_id=session.correlation_id,
                        failure_metadata={
                            "flow": flow,
                            "error_code": f"{flow.upper()}_TIMEOUT",
                            "error_message": f"{label} analysis timed out after {timeout_seconds // 60} minutes without worker response.",
                            "retry_count": 0,
                        },
                    )
                    if updated:
                        recovered_counts[flow] += 1
                        logger.warning(
                            "Timeout supervisor recovered stuck %s session | session_id=%s correlation_id=%s",
                            label,
                            session_id,
                            session.correlation_id,
                        )
                        await audit_service.log_event(
                            event=failed.value.upper(),
                            actor="timeout_supervisor",
                            actor_role="system",
                            session_id=session_id,
                            metadata={
                                "reason": "timeout",
                                "correlation_id": session.correlation_id,
                            },
                        )
                except Exception:
                    logger.exception(
                        "Timeout supervisor could not recover %s session %s", flow, session.id
                    )

        try:
            # In-process TIPSC work lost on reload/restart becomes explicitly retryable.
            tipsc_states = [
                "queued",
                "pre_eval",
                "validation_running",
                "regulatory_running",
                "ethics_running",
                "tipsc_running",
                "tipsc_reevaluation",
            ]
            stuck_tipsc = await Session.find(
                {
                    "status": {"$in": tipsc_states},
                    "updated_at": {"$lt": now - timedelta(seconds=timeout_seconds)},
                }
            ).to_list()
            for session in stuck_tipsc:
                updated = await session_repo.update_flow_failure(
                    session_id=str(session.id),
                    new_status=SessionStatus.TIPSC_FAILED,
                    expected_version=session.version,
                    correlation_id=session.correlation_id,
                    failure_metadata={
                        "flow": "tipsc",
                        "error_code": "TIPSC_TIMEOUT",
                        "error_message": "Pipeline timed out or its process stopped. Retry TIPSC.",
                        "retry_count": 0,
                    },
                )
                if updated:
                    from services.session_task_registry import cancel_session_task

                    cancel_session_task(str(session.id))

        except Exception as exc:
            logger.exception("Error in timeout supervisor execution: %s", exc)

        return recovered_counts

    async def _loop(self, check_interval_seconds: int = 60) -> None:
        while self._running:
            try:
                timeout_seconds = getattr(settings, "AGENT_TIMEOUT_SECONDS", 1800)
                await self.check_and_recover_stuck_sessions(timeout_seconds=timeout_seconds)
            except Exception as exc:
                logger.exception("Unexpected error in timeout supervisor loop: %s", exc)
            await asyncio.sleep(check_interval_seconds)

    def start(self, check_interval_seconds: int = 60) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(check_interval_seconds=check_interval_seconds))
        logger.info(
            "Timeout supervisor background task started (interval=%ds)", check_interval_seconds
        )

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Timeout supervisor background task stopped")


timeout_supervisor = TimeoutSupervisor()
