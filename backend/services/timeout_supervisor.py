"""
services/timeout_supervisor.py

Lightweight background supervisor that detects sessions stuck in waiting or running
states (e.g. DFV_WAITING, DISCOVERY_WAITING) past a configurable timeout window
and transitions DFV, Discovery, and PMF to their corresponding failure states.

Does NOT re-trigger agents, issue Kafka retries, or use DLQs.
Allows normal frontend user retries to start new runs with fresh correlation IDs.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from beanie.operators import In

from core.config import settings
from state_machine.states import SessionStatus
from repositories.session_repo import session_repo
from services.audit_service import audit_service
from models.session import Session

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def _normalize_utc(value: datetime) -> datetime:
    """
    Normalize a datetime to timezone-aware UTC.

    Assumption: naive datetimes stored in the database represent UTC.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


class TimeoutSupervisor:
    """Background supervisor for recovering timed-out flow sessions."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def check_and_recover_stuck_sessions(
        self,
        timeout_seconds: int = 1800,
    ) -> dict[str, int]:
        """
        Scan for sessions stuck in waiting or running states longer than
        timeout_seconds and transition them to their corresponding failure state.
        """
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        recovered_counts = {"dfv": 0, "discovery": 0, "pmf": 0}
        now = _utc_now()
        flows = {
            "dfv": (SessionStatus.DFV_WAITING, SessionStatus.DFV_RUNNING, SessionStatus.DFV_FAILED),
            "discovery": (SessionStatus.DISCOVERY_WAITING, SessionStatus.DISCOVERY_RUNNING, SessionStatus.DISCOVERY_FAILED),
            "pmf": (SessionStatus.PMF_WAITING, SessionStatus.PMF_RUNNING, SessionStatus.PMF_FAILED),
        }
        for flow, (waiting, running, failed) in flows.items():
            try:
                sessions = await Session.find(
                    In("status", [waiting.value, running.value])
                ).to_list()
            except Exception:
                logger.exception("Could not scan %s sessions for timeouts", flow)
                continue

            for session in sessions:
                try:
                    start_time = session.flow_started_at or session.updated_at
                    if not start_time or (now - _normalize_utc(start_time)).total_seconds() < timeout_seconds:
                        continue
                    session_id = str(session.id)
                    # Match the exact snapshot: a completed job or newer retry must survive.
                    updated = await session_repo.update_flow_failure(
                        session_id=session_id,
                        new_status=failed,
                        failure_metadata={
                            "flow": flow,
                            "error_code": f"{flow.upper()}_TIMEOUT",
                            "error_message": f"{flow.upper()} analysis timed out after {timeout_seconds} seconds without worker response.",
                            "retry_count": 0,
                        },
                        expected_version=session.version,
                        expected_status=session.status,
                        correlation_id=session.correlation_id,
                    )
                    if not updated:
                        continue
                    recovered_counts[flow] += 1
                    logger.warning(
                        "Timeout supervisor recovered %s session | session_id=%s correlation_id=%s",
                        flow, session_id, session.correlation_id,
                    )
                    await audit_service.log_event(
                        event=f"{flow.upper()}_FAILED",
                        actor="timeout_supervisor",
                        actor_role="system",
                        session_id=session_id,
                        metadata={"reason": "timeout", "correlation_id": session.correlation_id},
                    )
                except Exception:
                    logger.exception("Could not recover timed-out %s session %s", flow, session.id)
        return recovered_counts

    async def _loop(self, check_interval_seconds: int = 60) -> None:
        """Periodically check and recover timed-out sessions."""
        while self._running:
            try:
                timeout_seconds = getattr(
                    settings,
                    "AGENT_TIMEOUT_SECONDS",
                    1800,
                )

                await self.check_and_recover_stuck_sessions(
                    timeout_seconds=timeout_seconds,
                )

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(
                    "Unexpected error in timeout supervisor loop"
                )

            await asyncio.sleep(check_interval_seconds)

    def start(self, check_interval_seconds: int = 60) -> None:
        """Start the background supervisor if it is not already running."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(
            self._loop(
                check_interval_seconds=check_interval_seconds,
            )
        )

        logger.info(
            "Timeout supervisor background task started (interval=%ds)",
            check_interval_seconds,
        )

    async def stop(self) -> None:
        """Stop the background supervisor gracefully."""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass
            finally:
                self._task = None

        logger.info("Timeout supervisor background task stopped")


timeout_supervisor = TimeoutSupervisor()
