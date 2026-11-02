"""Kafka offsets must advance only after a worker message is handled."""

import pytest

from workers.combined_agent_worker import CombinedAgentWorker


class OneMessageConsumer:
    def __init__(self):
        self.commits = 0

    def __aiter__(self):
        self.remaining = 1
        return self

    async def __anext__(self):
        if not self.remaining:
            raise StopAsyncIteration
        self.remaining -= 1
        return type("Message", (), {"value": {"job": "test"}})()

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_failed_callback_does_not_commit_offset():
    worker = CombinedAgentWorker()
    worker.consumer_dfv = OneMessageConsumer()

    async def fail(_value):
        raise RuntimeError("backend unavailable")

    worker._handle_dfv = fail
    with pytest.raises(RuntimeError, match="backend unavailable"):
        await worker._consume_dfv()
    assert worker.consumer_dfv.commits == 0


@pytest.mark.asyncio
async def test_handled_message_commits_offset():
    worker = CombinedAgentWorker()
    worker.consumer_dfv = OneMessageConsumer()

    async def handle(_value):
        return None

    worker._handle_dfv = handle
    await worker._consume_dfv()
    assert worker.consumer_dfv.commits == 1
