from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import services.timeout_supervisor as module
from repositories.session_repo import session_repo
from state_machine.states import SessionStatus


@pytest.mark.asyncio
async def test_recovers_all_flows_and_preserves_active_sessions(monkeypatch):
    now = datetime.now(timezone.utc)
    def session(status, age, naive=False):
        started = now - timedelta(seconds=age)
        if naive:
            started = started.replace(tzinfo=None)
        return SimpleNamespace(id='test', status=status, version=7, correlation_id='run',
                               flow_started_at=started, updated_at=now)
    expired = session(SessionStatus.DFV_WAITING, 601, True)
    pmf = session(SessionStatus.PMF_RUNNING, 600)
    queries = [
        [expired, session(SessionStatus.DFV_RUNNING, 599)],
        [session(SessionStatus.DISCOVERY_WAITING, 100)], [pmf],
    ]
    find = Mock(side_effect=[SimpleNamespace(to_list=AsyncMock(return_value=rows)) for rows in queries])
    monkeypatch.setattr(module, 'Session', SimpleNamespace(find=find))
    monkeypatch.setattr(module, '_utc_now', lambda: now)
    update = AsyncMock(return_value=True)
    audit = AsyncMock()
    monkeypatch.setattr(module, 'session_repo', SimpleNamespace(update_flow_failure=update))
    monkeypatch.setattr(module, 'audit_service', SimpleNamespace(log_event=audit))
    counts = await module.TimeoutSupervisor().check_and_recover_stuck_sessions(600)
    assert counts == {'dfv': 1, 'discovery': 0, 'pmf': 1}
    assert update.call_args_list[0].kwargs['expected_version'] == 7
    assert update.call_args_list[0].kwargs['correlation_id'] == 'run'
    assert update.call_args_list[0].kwargs['expected_status'] == SessionStatus.DFV_WAITING
    assert update.call_args_list[1].kwargs['new_status'] == SessionStatus.PMF_FAILED
    assert audit.await_count == 2


@pytest.mark.asyncio
async def test_lost_race_is_not_counted_or_audited_and_errors_do_not_stop_scan(monkeypatch):
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    s = SimpleNamespace(id='test', status=SessionStatus.DFV_WAITING, version=1,
                        correlation_id='old', flow_started_at=None, updated_at=old)
    find = Mock(side_effect=[SimpleNamespace(to_list=AsyncMock(return_value=[s, s, s])),
                            SimpleNamespace(to_list=AsyncMock(return_value=[])),
                            SimpleNamespace(to_list=AsyncMock(return_value=[]))])
    monkeypatch.setattr(module, 'Session', SimpleNamespace(find=find))
    update = AsyncMock(side_effect=[RuntimeError('temporary DB error'), False, True])
    audit = AsyncMock()
    monkeypatch.setattr(module, 'session_repo', SimpleNamespace(update_flow_failure=update))
    monkeypatch.setattr(module, 'audit_service', SimpleNamespace(log_event=audit))
    counts = await module.TimeoutSupervisor().check_and_recover_stuck_sessions(600)
    assert counts['dfv'] == 1
    assert update.await_count == 3
    assert audit.await_count == 1


@pytest.mark.asyncio
async def test_repository_failure_update_guards_snapshot(monkeypatch):
    import repositories.session_repo as repository
    update = AsyncMock(return_value=SimpleNamespace(modified_count=0))
    find = Mock(return_value=SimpleNamespace(update=update))
    monkeypatch.setattr(repository, 'Session', SimpleNamespace(find_one=find))
    result = await session_repo.update_flow_failure(
        '0123456789abcdef01234567', SessionStatus.PMF_FAILED, {},
        expected_version=5, expected_status=SessionStatus.PMF_RUNNING, correlation_id='old-run')
    assert result is False
    query = find.call_args.args[0]
    assert query['version'] == 5
    assert query['status'] == 'pmf_running'
    assert query['correlation_id'] == 'old-run'
