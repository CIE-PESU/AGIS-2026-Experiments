"""Unknown customer measurements must remain unknown even if a model invents them."""

import importlib
import json
from pathlib import Path
from unittest.mock import MagicMock


def test_pmf_does_not_accept_fabricated_measurements(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "pmf-agent"))
    analyzer = importlib.import_module("pmf_analyzer")
    evidence = {"score": 50, "summary": "Hypothesis requiring customer evidence"}
    invented = {
        "pmf_score": 50,
        "verdict": "Unverified",
        "executive_summary": "Qualitative hypothesis",
        "sean_ellis_test": {
            "very_disappointed_percentage": 99,
            "meets_target": True,
            "analysis": "Invented survey",
        },
        "net_promoter_score": {
            "nps_score": 99,
            "meets_target": True,
            "promoters_ratio": "Invented responses",
        },
        "retention_analysis": {
            "curve_trajectory": "Flat",
            "value_creation_signal": "STRONG",
            "summary": "Invented cohort",
        },
        **{
            key: evidence
            for key in [
                "target_customer_alignment",
                "demand_validation",
                "value_proposition_strength",
                "defensibility_and_moat",
            ]
        },
        "key_strengths": [],
        "key_risks": ["No customer measurements supplied"],
    }
    monkeypatch.setattr(
        analyzer,
        "Crew",
        MagicMock(
            return_value=MagicMock(
                kickoff=MagicMock(return_value=MagicMock(raw=json.dumps(invented)))
            )
        ),
    )
    result = analyzer.run_pmf_analysis({"idea_name": "Test hypothesis"})
    agent = analyzer.Crew.call_args.kwargs["agents"][0]
    assert [skill.name for skill in agent.skills] == ["pmf-evaluator"]
    assert "Do not estimate survey responses" in agent.skills[0].instructions
    assert result["sean_ellis_test"]["very_disappointed_percentage"] is None
    assert result["sean_ellis_test"]["meets_target"] is None
    assert result["net_promoter_score"]["nps_score"] is None
    assert result["net_promoter_score"]["meets_target"] is None
    assert result["retention_analysis"]["curve_trajectory"] == "Unknown"
    assert result["retention_analysis"]["value_creation_signal"] == "UNKNOWN"
