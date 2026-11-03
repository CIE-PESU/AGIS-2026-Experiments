"""Run actual CrewAI agents with an offline model, verifying skill injection and schemas."""

import json
from pathlib import Path

import pytest
import yaml
from crewai import BaseLLM
from workers.combined_agent_worker import _load_discovery_agent, _load_module

ROOT = Path(__file__).resolve().parents[3]


class OfflineLLM(BaseLLM):
    def __init__(self, report):
        super().__init__(model="offline-agent-review")
        self.report = report
        self.prompts = []

    def call(self, messages, **kwargs):
        self.prompts.append(str(messages))
        return "Final Answer: " + json.dumps(self.report)

    def supports_function_calling(self):
        return False


@pytest.fixture
def preeval():
    from tipsc_models import PreEvalOutput

    return PreEvalOutput(
        problem_statement="Students lose time finding mentors.",
        customer_segment="Students",
        consequence="Delayed validation",
        assumptions=["Students need help"],
        proposed_solution="Mentor matching",
        target_geography="India",
        industry_sector="Education",
    )


@pytest.mark.parametrize(
    "stage", ["preeval", "validation", "regulatory", "ethics", "tipsc", "followup"]
)
def test_actual_tipsc_agents_receive_framework_instructions(monkeypatch, preeval, stage):
    import pipeline

    outputs = {
        "preeval": preeval.model_dump(),
        "validation": dict(
            target_geography="India",
            industry_sector="Education",
            checked_assumptions=[],
            competitor_landscape="Unverified",
            market_notes="Not measured",
            validation_summary="WEAK",
        ),
        "regulatory": dict(
            target_geography="India",
            industry_sector="Education",
            applicable_regulations=[],
            regulatory_summary="No verified requirements",
            requires_specialist_review=False,
            key_compliance_risks=[],
        ),
        "ethics": dict(
            harm_vector="GREEN",
            harm_reason="No structural harm",
            legal_risk="GREEN",
            legal_reason="No facial illegality",
            problem_solution_integrity="GREEN",
            integrity_reason="Aligned",
            ethics_pass=True,
            compliance_flag=False,
            rejection_reason="",
        ),
        "tipsc": dict(
            refined_idea=dict(
                customer_segment="Students",
                qualified_problem="Lost time",
                consequence="Delay",
                proposed_solution="Mentor matching",
            ),
            solution_alignment="GREEN",
            tips_validated_metrics=dict(
                timely_factor="Unknown",
                importance_metric="Delay",
                profitability_pivot="Unproven",
                solvability_constraint="Unknown",
            ),
            tips_rag_scores=dict(T="YELLOW", I="YELLOW", P="YELLOW", S="YELLOW"),
            overall_readiness="MODERATE",
            ready_for_dfv=False,
        ),
        "followup": dict(needs_followup=True, questions=["What evidence supports adoption?"]),
    }
    model = OfflineLLM(outputs[stage])
    config = ROOT / "TIPSC-Agent/src/config"
    agents = yaml.safe_load((config / "agents.yaml").read_text())
    tasks = yaml.safe_load((config / "tasks.yaml").read_text())
    monkeypatch.setattr(pipeline, "search_tool", None)
    if stage == "preeval":
        result = pipeline.run_preeval(model, preeval.model_dump())
    elif stage == "followup":
        result = pipeline.run_followup(model, preeval, agents, tasks)
    else:
        result = getattr(pipeline, f"run_{stage}")(model, preeval, agents, tasks)
    assert result.model_dump()
    skill = next(s for s in pipeline.activated if s.name == stage)
    assert skill.instructions.strip().splitlines()[0] in model.prompts[0]


def test_actual_dfv_crew_attaches_each_skill_and_validates_final_decision(monkeypatch):
    module = _load_module("dfv_offline_review", str(ROOT / "DFV-agent/main.py"))
    report = dict(
        refined_idea=dict(
            customer_segment="Students",
            qualified_problem="Lost time",
            consequence="Delay",
            proposed_solution="Mentor matching",
        ),
        hypotheses=dict(
            desirability_statement="Adoption hypothesis",
            feasibility_statement="Delivery hypothesis",
            viability_statement="Payment hypothesis",
        ),
        tips_validated_metrics=dict(
            timely_factor="Unknown",
            importance_metric="Delay",
            profitability_pivot="Unproven",
            solvability_constraint="Unknown",
        ),
        final_decision=dict(status="GO", justification="Deterministic offline test only"),
    )
    model = OfflineLLM(report)
    monkeypatch.setattr(module, "llm", model)
    result = module.run_analysis(
        {
            name: "Offline founder context {braces}"
            for name in ("desirability", "feasibility", "viability")
        }
    )
    assert result.validated.final_decision.status == "GO"
    assert len(model.prompts) == 4
    for skill in module.activated:
        assert any(skill.instructions.strip().splitlines()[0] in prompt for prompt in model.prompts)


def test_actual_discovery_crew_injects_interview_skill(monkeypatch):
    run = _load_discovery_agent()
    context = run.__globals__
    model = OfflineLLM({"interview_plan": "Explore past behavior and alternatives"})
    monkeypatch.setattr(context["customer_discovery_planner"], "llm", model)
    result = run(context["SAMPLE_DISCOVERY_INPUTS"])
    assert "interview_plan" in result.raw
    assert context["activated"][0].instructions.strip().splitlines()[0] in model.prompts[0]


def test_actual_quickstart_crew_validates_ten_parameters(monkeypatch):
    from typing import get_args

    from quickstart_agent import main
    from quickstart_agent.models import ParameterRating, QuickstartInput

    report = dict(
        parameters=[
            dict(name=name, rating="YELLOW", reason="Hypothesis requiring evidence")
            for name in get_args(ParameterRating.model_fields["name"].annotation)
        ],
        parameter_advice={},
        priority_advice=["Gather customer evidence"],
    )
    model = OfflineLLM(report)
    monkeypatch.setattr(main, "llm", model)
    monkeypatch.setattr(main, "tavily_tool", None)
    monkeypatch.setattr(main, "serper_tool", None)
    result = main.run_quickstart_eval(
        QuickstartInput(
            **{name: "Founder context {braces}" for name in QuickstartInput.model_fields}
        )
    )
    assert result.yellow_count == 10
    assert main.activated[0].instructions.strip().splitlines()[0] in model.prompts[0]
