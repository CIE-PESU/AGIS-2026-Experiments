"""Agent subprocess output and timeout handling without making LLM calls."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from workers import combined_agent_worker as worker_module


@pytest.mark.asyncio
async def test_agent_subprocess_reads_result_file(monkeypatch):
    async def create(*args, **kwargs):
        Path(args[-1]).write_text(json.dumps({"decision": "GO"}))

        class Process:
            returncode = 0

            async def communicate(self, payload):
                assert json.loads(payload) == {"idea": "test"}
                return b"", b""

        return Process()

    monkeypatch.setattr(worker_module.asyncio, "create_subprocess_exec", create)
    assert await worker_module._run_agent_subprocess("dfv", {"idea": "test"}) == {"decision": "GO"}


@pytest.mark.asyncio
async def test_agent_subprocess_is_killed_on_timeout(monkeypatch):
    process = SimpleNamespace(pid=12345, returncode=None)
    killed = []

    async def communicate(_payload):
        await asyncio.sleep(1)

    async def wait():
        process.returncode = -9

    process.communicate = communicate
    process.wait = wait
    process.kill = lambda: killed.append("windows")

    async def create(*_args, **_kwargs):
        return process

    monkeypatch.setattr(worker_module.asyncio, "create_subprocess_exec", create)
    monkeypatch.setattr(worker_module, "settings", SimpleNamespace(AGENT_TIMEOUT_SECONDS=0.01))
    monkeypatch.setattr(worker_module.os, "killpg", lambda *_args: killed.append("unix"), raising=False)

    with pytest.raises(asyncio.TimeoutError):
        await worker_module._run_agent_subprocess("dfv", {})
    assert killed
