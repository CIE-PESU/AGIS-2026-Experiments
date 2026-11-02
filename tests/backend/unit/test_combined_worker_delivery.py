"""Kafka offsets advance only after durable callback delivery succeeds."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiokafka.structs import TopicPartition

from workers.combined_agent_worker import CombinedAgentWorker


class OneMessageConsumer:
    def __init__(self):
        self.commits = []
        self.partition = TopicPartition("userSession.pmf", 0)

    def __aiter__(self):
        self.remaining = 1
        return self

    async def __anext__(self):
        if not self.remaining:
            raise StopAsyncIteration
        self.remaining -= 1
        return SimpleNamespace(value={"job": "test"}, topic=self.partition.topic, partition=0, offset=3)

    def assignment(self):
        return {self.partition}

    def pause(self, *_partitions):
        pass

    def resume(self, *_partitions):
        pass

    async def getmany(self, **_kwargs):
        return {}

    async def commit(self, offsets):
        self.commits.append(offsets)


@pytest.mark.asyncio
async def test_cancelled_callback_does_not_commit_offset():
    worker = CombinedAgentWorker()
    worker.consumer_pmf = OneMessageConsumer()
    worker._handle_pmf = AsyncMock(side_effect=asyncio.CancelledError)
    with pytest.raises(asyncio.CancelledError):
        await worker._consume_pmf()
    assert worker.consumer_pmf.commits == []


@pytest.mark.asyncio
async def test_callback_retries_before_committing_offset(monkeypatch):
    worker = CombinedAgentWorker()
    worker.consumer_pmf = OneMessageConsumer()
    worker._handle_pmf = AsyncMock(side_effect=[RuntimeError("backend unavailable"), None])
    monkeypatch.setattr("workers.combined_agent_worker.asyncio.sleep", AsyncMock())
    await worker._consume_pmf()
    assert worker._handle_pmf.await_count == 2
    assert worker.consumer_pmf.commits == [{worker.consumer_pmf.partition: 4}]
