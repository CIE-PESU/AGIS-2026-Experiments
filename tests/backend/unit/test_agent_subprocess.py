"""Agent subprocess output and timeout handling without making LLM calls."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from workers import combined_agent_worker as worker_module


@pytest.mark.asyncio
async def test_agent_subprocess_reads_result_file(monkeypatch):
    monkeypatch.setattr(worker_module, "ProcessTree", MagicMock())

    async def create(*args, **kwargs):
        Path(args[-1]).write_text(json.dumps({"decision": "GO"}))

        class Process:
            pid = 12345
            returncode = 0

            async def wait(self):
                return 0

            async def communicate(self, payload):
                assert json.loads(payload) == {"idea": "test"}
                return b"", b""

        return Process()

    monkeypatch.setattr(worker_module.asyncio, "create_subprocess_exec", create)
    assert await worker_module.CombinedAgentWorker()._run_agent("dfv", {"idea": "test"}) == {
        "decision": "GO"
    }


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
    tree = MagicMock()
    tree.terminate.side_effect = lambda **_: killed.append("tree")
    monkeypatch.setattr(worker_module, "ProcessTree", lambda _: tree)

    with pytest.raises(asyncio.TimeoutError):
        await worker_module.CombinedAgentWorker()._run_agent("dfv", {})
    assert killed


def test_agent_imports_do_not_replace_shared_provider_functions():
    import importlib
    from pathlib import Path

    import litellm
    from crewai import LLM
    from crewai.llms import cache
    from workers.combined_agent_worker import _load_module

    original = (
        litellm.drop_params,
        litellm.completion,
        litellm.acompletion,
        LLM.supports_function_calling,
        cache.mark_cache_breakpoint,
    )
    root = Path(__file__).resolve().parents[3]
    _load_module("agis_dfv_import_regression", str(root / "DFV-agent" / "main.py"))
    importlib.import_module("quickstart_agent.main")
    _load_module(
        "agis_discovery_import_regression",
        str(root / "customer-interview-planner-agent" / "customer_interview_planner.py"),
    )
    assert original == (
        litellm.drop_params,
        litellm.completion,
        litellm.acompletion,
        LLM.supports_function_calling,
        cache.mark_cache_breakpoint,
    )
