"""Regressions at AGIS agent boundaries; no model or search requests."""

import importlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_dispatcher_passes_founder_context_through_worker_thread():
    from engine.dispatcher.dispatcher import WorkerDispatcher

    stages = SimpleNamespace(execute_tipsc=MagicMock(return_value="assessment"))
    dispatcher = WorkerDispatcher(stages)
    assert (
        await dispatcher.dispatch_tipsc("idea", "validation", "compliance", "prior answer")
        == "assessment"
    )
    stages.execute_tipsc.assert_called_once_with("idea", "validation", "compliance", "prior answer")


def test_json_call_preserves_system_instructions_without_mutating_messages():
    import pipeline

    messages = [
        {"role": "system", "content": "Do not infer missing facts."},
        {"role": "user", "content": "Evaluate the supplied idea."},
    ]
    original = [dict(m) for m in messages]
    llm = SimpleNamespace(call=MagicMock(return_value='{"ok": true}'))
    assert json.loads(pipeline.call_llm_for_json(llm, messages)) == {"ok": True}
    sent = llm.call.call_args.args[0]
    assert "Do not infer missing facts." in sent[0]["content"]
    assert pipeline.JSON_SYSTEM_PREFIX in sent[0]["content"]
    assert sent[1:] == messages[1:]
    assert messages == original


@pytest.mark.parametrize("wrapper", ["competitor_landscape", "research"])
def test_validation_unwraps_nested_assessment_even_under_known_key(wrapper):
    import pipeline

    preeval = SimpleNamespace(target_geography="India", industry_sector="Education")
    actual = {
        "checked_assumptions": [
            {"assumption": "Need", "verdict": "CONFIRMED", "evidence": "Source"}
        ],
        "competitor_landscape": "An existing competitor",
        "validation_summary": "STRONG",
    }
    normalized = pipeline.normalize_validation_dict({wrapper: actual}, preeval)
    assert normalized["checked_assumptions"][0]["verdict"] == "CONFIRMED"
    assert normalized["validation_summary"] == "STRONG"
    assert normalized["competitor_landscape"] == "An existing competitor"


@pytest.mark.parametrize("module", ["quickstart_agent.main", "workers.combined_agent_worker"])
@pytest.mark.parametrize(
    "raw",
    [
        'Here is the result:\n```json\n{"decision":"GO", "reason":"a } brace"}\n```\nDone.',
        '{"decision":"GO", "reason":"a } brace"}\nDone.',
    ],
)
def test_output_parser_handles_surrounding_prose_and_braces_inside_strings(module, raw):
    parser = importlib.import_module(module)._extract_json_block
    assert json.loads(parser(raw)) == {"decision": "GO", "reason": "a } brace"}


@pytest.mark.parametrize(
    "raw", ['[{"decision":"GO"}]', '{"broken": invalid, "partial": {"decision":"GO"}}']
)
def test_worker_rejects_arrays_and_does_not_salvage_nested_partial_results(raw):
    from workers.combined_agent_worker import _parse_agent_output

    with pytest.raises(ValueError):
        _parse_agent_output(raw)


@pytest.mark.asyncio
async def test_quickstart_returns_validated_agent_output_directly(monkeypatch):
    from quickstart_agent import main
    from quickstart_agent.models import QuickstartInput
    from routes.v1.quickstart import run_quickstart_agent

    data = QuickstartInput(**{k: "Supplied context" for k in QuickstartInput.model_fields})
    result = object()
    run = AsyncMock(return_value=result)
    monkeypatch.setattr(main, "run_quickstart_eval_async", run)
    assert await run_quickstart_agent(data) is result
    run.assert_awaited_once_with(data)
