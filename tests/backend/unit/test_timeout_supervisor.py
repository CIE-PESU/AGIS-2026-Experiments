from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.timeout_supervisor import TimeoutSupervisor, _as_utc
from state_machine.states import SessionStatus


def test_as_utc_handles_mongodb_naive_and_aware_timestamps():
    naive = datetime(2026, 10, 27, 12, 0)
    assert _as_utc(naive) == naive.replace(tzinfo=UTC)
    assert _as_utc(datetime(2026, 10, 27, 17, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))) == naive.replace(tzinfo=UTC)


@pytest.mark.asyncio
async def test_recovers_dfv_and_discovery_with_naive_mongodb_timestamps():
    old = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
    dfv = SimpleNamespace(version=0, id="dfv-id", flow_started_at=old, updated_at=old, correlation_id="dfv-correlation")
    discovery = SimpleNamespace(version=0, id="discovery-id", flow_started_at=None, updated_at=old, correlation_id="discovery-correlation")
    queries = [MagicMock(to_list=AsyncMock(return_value=[dfv])), MagicMock(to_list=AsyncMock(return_value=[discovery])), MagicMock(to_list=AsyncMock(return_value=[]))]

    with (
        patch("services.timeout_supervisor.Session.find", side_effect=queries),
        patch("services.timeout_supervisor.session_repo.update_flow_failure", new_callable=AsyncMock, return_value=True) as update,
        patch("services.timeout_supervisor.audit_service.log_event", new_callable=AsyncMock),
    ):
        result = await TimeoutSupervisor().check_and_recover_stuck_sessions(timeout_seconds=1800)

    assert result == {"dfv": 1, "discovery": 1}
    assert [call.kwargs["new_status"] for call in update.await_args_list] == [SessionStatus.DFV_FAILED, SessionStatus.DISCOVERY_FAILED]
