"""Exercise the real CrewAI workflow with an offline model, plus output failures."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError


@pytest.fixture
def analyzer(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("CREWAI_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    path = Path(__file__).resolve().parents[2] / "pmf-agent" / "pmf_analyzer.py"
    spec = importlib.util.spec_from_file_location("pmf_analyzer_test", path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def report():
    return {
        "pmf_score": 35,
        "verdict": "Early Stage / Low PMF Fit",
        "executive_summary": "Qualitative assessment: founder hypotheses only.",
        # Deliberately unsupported measurements must be cleared by the application.
        "sean_ellis_test": {
            "very_disappointed_percentage": 70, "meets_target": True, "analysis": "Estimated",
        },
        "net_promoter_score": {
            "nps_score": 60, "meets_target": True, "promoters_ratio": "Estimated",
        },
        "retention_analysis": {
            "curve_trajectory": "Flattening", "value_creation_signal": "STRONG",
            "summary": "Assumed retention",
        },
        **{name: {"score": 35, "summary": "Founder hypothesis; unvalidated."} for name in (
            "target_customer_alignment", "demand_validation", "value_proposition_strength",
            "defensibility_and_moat",
        )},
        "key_strengths": ["Specific customer segment named."],
        "key_risks": ["No measured adoption evidence supplied."],
    }


def test_real_crew_runs_agent_task_and_preserves_measurement_rules(analyzer, report, monkeypatch):
    import crewai
    from crewai import BaseLLM

    class OfflineLLM(BaseLLM):
        def __init__(self):
            super().__init__(model="offline-pmf-test")
            self.prompts = []

        def call(self, messages, **kwargs):
            self.prompts.append(str(messages))
            return "Final Answer: " + json.dumps(report)

        def supports_function_calling(self):
            return False

    model = OfflineLLM()
    monkeypatch.setattr(crewai, "LLM", lambda **kwargs: model)
    inputs = {"idea_name": "Offline startup {example}", "problem_statement": "Founder hypothesis"}
    result = analyzer.run_pmf_analysis(inputs)

    assert model.prompts  # Actual Crew -> Agent -> offline model execution.
    assert inputs["idea_name"] in model.prompts[0]
    # This phrase exists only in SKILL.md: activation must reach the actual model context.
    assert "PMF evidence provenance protocol" in model.prompts[0]
    assert result["pmf_score"] == 35
    assert result["key_risks"] == report["key_risks"]
    assert result["sean_ellis_test"]["very_disappointed_percentage"] is None
    assert result["sean_ellis_test"]["meets_target"] is None
    assert result["net_promoter_score"]["nps_score"] is None
    assert result["net_promoter_score"]["meets_target"] is None
    assert result["retention_analysis"]["curve_trajectory"] == "Unknown"
    assert result["retention_analysis"]["value_creation_signal"] == "UNKNOWN"
    analyzer.PMFAnalysis.model_validate(result)


def test_missing_pmf_skill_fails_clearly(analyzer, monkeypatch):
    import crewai.skills

    monkeypatch.setattr(crewai.skills, "discover_skills", lambda path: [])
    with pytest.raises(ValueError, match="Required pmf-evaluator skill not found"):
        analyzer.run_pmf_analysis({"idea_name": "Test"})


@pytest.mark.parametrize("invalid", [False, True])
def test_raw_crew_output_fallback_is_validated(analyzer, report, monkeypatch, invalid):
    import crewai

    if invalid:
        report["pmf_score"] = 101

    class RawOutputCrew:
        def __init__(self, **kwargs):
            pass

        def kickoff(self, inputs):
            return SimpleNamespace(pydantic=None, raw="```json\n" + json.dumps(report) + "\n```")

    monkeypatch.setattr(crewai, "LLM", lambda **kwargs: "openai/test-model")
    monkeypatch.setattr(analyzer, "Crew", RawOutputCrew)
    if invalid:
        with pytest.raises(ValidationError):
            analyzer.run_pmf_analysis({"idea_name": "Test"})
    else:
        assert analyzer.run_pmf_analysis({"idea_name": "Test"})["pmf_score"] == 35
