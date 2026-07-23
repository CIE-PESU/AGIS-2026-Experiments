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
from datetime import datetime, timezone, timedelta
from typing import Optional

from beanie.operators import In

from core.config import settings
from state_machine.states import SessionStatus
from repositories.session_repo import session_repo
from services.audit_service import audit_service
from models.session import Session

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
        Scan for sessions stuck in waiting or running state longer than timeout_seconds
        and transition them to DFV_FAILED / DISCOVERY_FAILED.
        """
        now = _utc_now()
        recovered_counts = {"dfv": 0, "discovery": 0}

        try:
            # 1. Recover stuck DFV sessions using flow_started_at (fallback to updated_at if flow_started_at is None)
            stuck_dfv = await Session.find(
                In("status", [SessionStatus.DFV_WAITING.value, SessionStatus.DFV_RUNNING.value]),
            ).to_list()

            for session in stuck_dfv:
                start_time = session.flow_started_at or session.updated_at
                if not start_time or (now - start_time) < timedelta(seconds=timeout_seconds):
                    continue

                session_id = str(session.id)
                # Atomic CAS update for recovery: target ONLY if status is STILL DFV_WAITING/DFV_RUNNING
                updated = await session_repo.update_flow_failure(
                    session_id=session_id,
                    new_status=SessionStatus.DFV_FAILED,
                    failure_metadata={
                        "flow": "dfv",
                        "error_code": "DFV_TIMEOUT",
                        "error_message": f"DFV analysis timed out after {timeout_seconds // 60} minutes without worker response.",
                        "retry_count": 0,
                    },
                )
                if updated:
                    recovered_counts["dfv"] += 1
                    logger.warning(
                        "Timeout supervisor recovered stuck DFV session | session_id=%s correlation_id=%s",
                        session_id,
                        session.correlation_id,
                    )
                    await audit_service.log_event(
                        event="DFV_FAILED",
                        actor="timeout_supervisor",
                        actor_role="system",
                        session_id=session_id,
                        metadata={
                            "reason": "timeout",
                            "correlation_id": session.correlation_id,
                        },
                    )

            # 2. Recover stuck Discovery sessions using flow_started_at (fallback to updated_at if flow_started_at is None)
            stuck_discovery = await Session.find(
                In("status", [SessionStatus.DISCOVERY_WAITING.value, SessionStatus.DISCOVERY_RUNNING.value]),
            ).to_list()

            for session in stuck_discovery:
                start_time = session.flow_started_at or session.updated_at
                if not start_time or (now - start_time) < timedelta(seconds=timeout_seconds):
                    continue

                session_id = str(session.id)
                # Atomic CAS update for recovery: target ONLY if status is STILL DISCOVERY_WAITING/DISCOVERY_RUNNING
                updated = await session_repo.update_flow_failure(
                    session_id=session_id,
                    new_status=SessionStatus.DISCOVERY_FAILED,
                    failure_metadata={
                        "flow": "discovery",
                        "error_code": "DISCOVERY_TIMEOUT",
                        "error_message": f"Discovery analysis timed out after {timeout_seconds // 60} minutes without worker response.",
                        "retry_count": 0,
                    },
                )
                if updated:
                    recovered_counts["discovery"] += 1
                    logger.warning(
                        "Timeout supervisor recovered stuck Discovery session | session_id=%s correlation_id=%s",
                        session_id,
                        session.correlation_id,
                    )
                    await audit_service.log_event(
                        event="DISCOVERY_FAILED",
                        actor="timeout_supervisor",
                        actor_role="system",
                        session_id=session_id,
                        metadata={
                            "reason": "timeout",
                            "correlation_id": session.correlation_id,
                        },
                    )

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
        logger.info("Timeout supervisor background task started (interval=%ds)", check_interval_seconds)

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
