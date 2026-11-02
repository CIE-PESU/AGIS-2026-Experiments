"""Failed startup/shutdown must not leave duplicate consumers or background jobs."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from workers import combined_agent_worker as module


async def test_startup_retry_closes_failed_consumer_first(monkeypatch):
    consumers = []
    def create(*_args, **_kwargs):
        if len(consumers) == 1:
            consumers[0].stop.assert_awaited_once()
        consumer = SimpleNamespace(start=AsyncMock(side_effect=RuntimeError("broker offline") if not consumers else None), stop=AsyncMock())
        consumers.append(consumer)
        return consumer
    monkeypatch.setattr(module, "AIOKafkaConsumer", create)
    monkeypatch.setattr(module, "AIOKafkaProducer", lambda **_: SimpleNamespace(start=AsyncMock(), stop=AsyncMock()))
    monkeypatch.setattr(module.asyncio, "sleep", AsyncMock())
    monkeypatch.setenv("WORKER_HEALTH_PORT", "0")
    worker = module.CombinedAgentWorker()
    try:
        await worker.start()
        assert len(consumers) == 4
    finally:
        await worker.stop()
    for consumer in consumers:
        consumer.stop.assert_awaited_once()


async def test_consumer_failure_cancels_sibling_jobs_before_cleanup(monkeypatch, tmp_path):
    monkeypatch.setenv("AGIS_RUNTIME_DIR", str(tmp_path))
    worker = module.CombinedAgentWorker()
    worker.start = AsyncMock()
    worker.stop = AsyncMock()
    stopped = []
    async def fail():
        await asyncio.sleep(0)
        raise RuntimeError("consumer failed")
    async def wait_for_cancel():
        try:
            await asyncio.Event().wait()
        finally:
            stopped.append(True)
    worker._consume_dfv = fail
    worker._consume_discovery = wait_for_cancel
    worker._consume_pmf = wait_for_cancel
    with pytest.raises(RuntimeError, match="consumer failed"):
        await worker.run()
    assert stopped == [True, True]
    worker.stop.assert_awaited_once()


async def test_cleanup_attempts_every_resource_even_when_one_fails():
    worker = module.CombinedAgentWorker()
    worker.consumer_dfv = SimpleNamespace(stop=AsyncMock(side_effect=RuntimeError("stop failed")))
    worker.consumer_pmf = SimpleNamespace(stop=AsyncMock())
    worker.producer = SimpleNamespace(stop=AsyncMock())
    worker.http_client = SimpleNamespace(aclose=AsyncMock())
    await worker.stop()
    worker.consumer_pmf.stop.assert_awaited_once()
    worker.producer.stop.assert_awaited_once()
    worker.http_client.aclose.assert_awaited_once()
