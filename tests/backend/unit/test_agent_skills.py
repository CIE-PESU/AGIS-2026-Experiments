"""Exercise agent construction with real skill loading, without provider calls."""

import importlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import yaml
from crewai import LLM
from crewai.skills import activate_skill, discover_skills

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("directory", "expected"),
    [
        ("DFV-agent/skills", ["d-skills", "evaluator-skills", "f-skills", "v-skills"]),
        ("customer-interview-planner-agent/skills", ["jtbd-interview-planner"]),
        ("pmf-agent/skills", ["pmf-evaluator"]),
        ("quickstart-agent/quickstart_agent/skills", ["quickstart-skill"]),
        (
            "TIPSC-Agent/src/skills",
            ["ethics", "followup", "preeval", "regulatory", "tipsc", "validation"],
        ),
    ],
)
def test_local_skills_are_discoverable_in_assignment_order(directory, expected):
    skills = discover_skills(ROOT / directory)
    activated = [activate_skill(s) for s in skills]
    assert [s.name for s in activated] == expected
    assert all(s.instructions and s.instructions.strip() for s in activated)


@pytest.mark.parametrize(
    "stage", ["preeval", "validation", "regulatory", "ethics", "tipsc", "followup"]
)
def test_tipsc_stage_receives_its_activated_skill(monkeypatch, stage):
    pipeline = importlib.import_module("pipeline")
    config = ROOT / "TIPSC-Agent/src/config"
    agents_cfg = yaml.safe_load((config / "agents.yaml").read_text())
    task_cfg = yaml.safe_load((config / "tasks.yaml").read_text())
    llm = LLM(model="openai/test-model", api_key="test-only")
    crew = MagicMock()
    crew.return_value.kickoff.side_effect = RuntimeError("stop before provider call")
    monkeypatch.setattr(pipeline, "Crew", crew)
    preeval = pipeline.PreEvalOutput(
        problem_statement="Lost time",
        customer_segment="Students",
        consequence="Delay",
        assumptions=["Students need help"],
        proposed_solution="Planner",
        target_geography="India",
        industry_sector="Education",
    )
    if stage == "preeval":
        args = (llm, preeval.model_dump())
    elif stage == "followup":
        args = (llm, SimpleNamespace(model_dump_json=lambda **kwargs: "{}"), agents_cfg, task_cfg)
    else:
        args = (llm, preeval, agents_cfg, task_cfg)
    with pytest.raises(RuntimeError, match="stop before provider call"):
        getattr(pipeline, f"run_{stage}")(*args)
    agent = crew.call_args.kwargs["agents"][0]
    assert [s.name for s in agent.skills] == [stage]
    assert agent.skills[0].instructions


def test_quickstart_attaches_skill_to_agent():
    module = importlib.import_module("quickstart_agent.main")
    crew = module.create_crew()
    assert [s.name for s in crew.agents[0].skills] == ["quickstart-skill"]
    assert "## Your Role" in crew.agents[0].skills[0].instructions
    assert "## Your Role" not in crew.tasks[0].description
