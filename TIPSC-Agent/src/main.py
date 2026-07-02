#!/usr/bin/env python3
"""Pre-Eval -> TIPSC pipeline using crewAI with local LLM (LM Studio)."""

import os,re

os.environ["OPENAI_API_KEY"] = "lm-studio"
os.environ["OPENAI_MODEL_NAME"] = "openai/qwen/qwen3.5-9b"

import json
import sys
from pathlib import Path

import yaml
from crewai import Agent, Crew, LLM, Process, Task
from crewai_tools import TavilySearchTool
from models import PreEvalOutput, TIPSCOutput, FollowUpOutput, EthicsOutput, ValidationOutput, RegulatoryOutput

from engine.stages import PipelineStages
from engine.pipeline_executor import PipelineExecutor

from pipeline import (
    run_tipsc,
    run_followup,
)

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

BASE_DIR = Path(__file__).resolve().parent

os.environ["TAVILY_API_KEY"] = "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"   # ← paste your key
search_tool = TavilySearchTool()

# ── Helpers ────────────────────────────────────


def load_yaml(rel: str) -> dict:
    path = BASE_DIR / rel
    if not path.exists():
        print(f"ERROR: config not found: {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_text(rel: str) -> str:
    path = BASE_DIR / rel
    if not path.exists():
        print(f"ERROR: file not found: {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return f.read()


def save_json(data, filename: str) -> Path:
    out_dir = BASE_DIR / ".." / "outputs"
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  Saved: {path}")
    return path


# ── LLM ────────────────────────────────────────


def load_llm() -> LLM:
    base_url = os.environ.get("LM_STUDIO_URL", "http://10.14.140.79:1234/v1")
    return LLM(
        model="openai/qwen/qwen3.5-9b",
        base_url="http://10.14.140.79:1234/v1",
        api_key="lm-studio",
        temperature=0.2,
    )


def print_validation_summary(val: ValidationOutput) -> None:
    verdict_icon = lambda v: "✅" if v == "CONFIRMED" else ("❓" if v == "UNCONFIRMED" else "❌")
    summary_icon = {"STRONG": "✅", "MIXED": "⚠️ ", "WEAK": "❌"}

    print(f"  Geography: {val.target_geography}  |  Sector: {val.industry_sector}")
    print(f"  Overall: {summary_icon.get(val.validation_summary, '')} {val.validation_summary}")
    print()
    for ac in val.checked_assumptions:
        print(f"  {verdict_icon(ac.verdict)} [{ac.verdict}] {ac.assumption}")
        print(f"      {ac.evidence}")
    print(f"\n  Competitors: {val.competitor_landscape}")
    if val.market_notes:
        print(f"  Market notes: {val.market_notes}")

 
def print_regulatory_summary(reg: "RegulatoryOutput") -> None:
    burden_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
    print(f"  Geography: {reg.target_geography}  |  Sector: {reg.industry_sector}")
    print(f"  Specialist review required: {'⚠️  Yes' if reg.requires_specialist_review else '✅ No'}")
    if reg.applicable_regulations:
        print()
        for r in reg.applicable_regulations:
            icon = burden_icon.get(r.compliance_burden, "")
            print(f"  {icon} [{r.compliance_burden}] {r.name} ({r.jurisdiction})")
            print(f"      {r.brief_requirement}")
    else:
        print("  No specific regulations identified.")
    if reg.key_compliance_risks:
        print(f"\n  Key risks:")
        for risk in reg.key_compliance_risks:
            print(f"    • {risk}")
    print(f"\n  Summary: {reg.regulatory_summary}")

 
def print_ethics_result(ethics: EthicsOutput) -> None:
    gate_icon = lambda score: "✅" if score == "GREEN" else ("⚠️ " if score == "YELLOW" else "❌")
 
    print(f"\n  Harm Vector:              {gate_icon(ethics.harm_vector)} {ethics.harm_vector}")
    print(f"    {ethics.harm_reason}")
    print(f"  Legal Risk:               {gate_icon(ethics.legal_risk)} {ethics.legal_risk}")
    print(f"    {ethics.legal_reason}")
    print(f"  Problem-Solution Integrity: {gate_icon(ethics.problem_solution_integrity)} {ethics.problem_solution_integrity}")
    print(f"    {ethics.integrity_reason}")
 
    if ethics.compliance_flag:
        print("\n  ⚠️  COMPLIANCE FLAG: This idea operates in a regulated space.")
        print("     Ensure legal/compliance review before DFV.")


def print_tipsc_summary(tips_out: TIPSCOutput) -> None:
    m = tips_out.tips_validated_metrics
    s = tips_out.tips_rag_scores
    print(f"  T: {m.timely_factor}")
    print(f"  I: {m.importance_metric}")
    print(f"  P: {m.profitability_pivot}")
    print(f"  S: {m.solvability_constraint}")
    print(f"\n  Scores → T={s.T}  I={s.I}  P={s.P}  S={s.S}")
    print(f"  Readiness: {tips_out.overall_readiness}  |  DFV: {tips_out.ready_for_dfv}")


# ── Entry point ────────────────────────────────


def main():
    agents_cfg = load_yaml("config/agents.yaml")
    task_cfg = load_yaml("config/tasks.yaml")
    preeval_skill = load_text("skills/preeval/SKILL.md")
    tipsc_rubric = load_text("skills/tipsc/SKILL.md")
    ethics_rubric = load_text("skills/ethics/SKILL.md")

    llm=load_llm()

    stages = PipelineStages(
        llm=llm,
        agents_cfg=agents_cfg,
        task_cfg=task_cfg,
        preeval_skill=preeval_skill,
        tipsc_rubric=tipsc_rubric,
        ethics_rubric=ethics_rubric,
    )


    # Quick connectivity check
    try:
        llm.call([{"role": "user",
                    "content": "Respond with one word: ok."}])
    except Exception as e:
        url = os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1")
        print(f"ERROR: Cannot reach LM Studio at {url}. Is the server running?")
        print(f"  Details: {e}")
        sys.exit(1)

    print("=" * 60)
    print("PHASE 1: Pre-Evaluation")
    print("=" * 60)

    preeval_input = {
        "problem_statement": input("Problem Statement: "),
        "customer_segment": input("Customer Segment: "),
        "consequence": input("Consequence: "),
        "assumptions": input("Assumptions: "),
        "proposed_solution": input("Proposed Solution: "),
        "target_geography": input("Target Geography: "),
        "industry_sector": input("Industry Sector: "),
    } 

    executor = PipelineExecutor(stages)
    results= executor.run(preeval_input)


    preeval_out = results["preeval"]
    save_json(preeval_out.model_dump(), "preeval_output.json")

    print("\n" + "=" * 60)
    print("PHASE 2: Market Validation")
    print("=" * 60)
    validation_out = results["validation"]
    save_json(validation_out.model_dump(), "validation_output.json")
    print_validation_summary(validation_out)
    validation_context = validation_out.model_dump_json(indent=2)

    print("\n" + "=" * 60)
    print("PHASE 3: Regulatory Mapping")
    print("=" * 60)
    regulatory_out = results["regulatory"]
    save_json(regulatory_out.model_dump(), "regulatory_output.json")
    print_regulatory_summary(regulatory_out)
    regulatory_context = regulatory_out.model_dump_json(indent=2)

    print("\n" + "=" * 60)
    print("PHASE 4: Ethics Pre-Screen")
    print("=" * 60)
    ethics_out = results["ethics"]
    save_json(ethics_out.model_dump(), "ethics_output.json")
 
    print_ethics_result(ethics_out)

    if regulatory_out.requires_specialist_review and not ethics_out.compliance_flag:
        ethics_out.compliance_flag = True
        print("  [Auto-correct] compliance_flag: False -> True (requires_specialist_review override)")  
 
    if not ethics_out.ethics_pass:
        print("\n" + "=" * 60)
        print("❌  IDEA REJECTED AT ETHICS GATE")
        print("=" * 60)
        print(f"  Reason: {ethics_out.rejection_reason}")
        print("\n  This idea will not proceed to TIPSC evaluation.")
        print("\nDone.")
        sys.exit(0)
 
    print("\n  ✅ Ethics gate passed. Proceeding to TIPSC evaluation.")

    compliance_context = results["compliance_context"]
    if compliance_context:
        print("\n  ⚠️  Compliance context built — will inform TIPSC S-dimension scoring.")

    print("\n" + "=" * 60)
    print("PHASE 5: TIPSC Evaluation")
    print("=" * 60)
    tips_out = results["tipsc"]
    save_json(tips_out.model_dump(), "tipsc_output.json")
    print()
    print_tipsc_summary(tips_out)
    
    MAX_FOLLOWUP_TURNS = 3
    followup_context= ""

    for turn in range(MAX_FOLLOWUP_TURNS):

        followup = run_followup(
        llm,
        tips_out,
        agents_cfg,
        task_cfg,
        followup_context=followup_context,
        compliance_context=compliance_context,
        )

        if not followup.needs_followup:
            print("\n  No further follow-up needed.")
            break

        if not followup.questions:
            print("  Warning: follow-up requested but no questions provided.")
            break

        question = followup.questions[0]

        print("\n" + "=" * 60)
        print(f"FOLLOW-UP QUESTION ({turn + 1}/{MAX_FOLLOWUP_TURNS})")
        print("=" * 60)

        print(question)

        answer = input("> ").strip()

        if not answer:
            answer = "(no answer provided)"


 
        followup_context += f"""
        Follow-up Question {turn+1}:
        {question}

        Founder Answer:
        {answer}
        """

        print("\nRe-evaluating TIPSC with new information...\n")

        tips_out = run_tipsc(
            llm,
            preeval_out,
            agents_cfg,
            task_cfg,
            tipsc_rubric,
            validation_context=validation_context,
            compliance_context=compliance_context,
            followup_context=followup_context,
        )
        print_tipsc_summary(tips_out)

    # after the follow-up loop ends, save the final tips_out
    save_json(tips_out.model_dump(), "tipsc_output_final.json") 


    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  T (Timely):      {tips_out.tips_rag_scores.T}")
    print(f"  I (Important):   {tips_out.tips_rag_scores.I}")
    print(f"  P (Profitable):  {tips_out.tips_rag_scores.P}")
    print(f"  S (Solvable):    {tips_out.tips_rag_scores.S}")
    print(f"  Readiness:       {tips_out.overall_readiness}")
    print(f"  Ready for DFV:   {tips_out.ready_for_dfv}")

    if ethics_out.compliance_flag:
        print("\n" + "=" * 60)
        print("⚠️  COMPLIANCE NOTICE")
        print("=" * 60)
        print(f"  Legal risk:  {ethics_out.legal_risk} — {ethics_out.legal_reason}")
        if regulatory_out.applicable_regulations:
            burden_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
            print("\n  Regulations flagged:")
            for r in regulatory_out.applicable_regulations:
                icon = burden_icon.get(r.compliance_burden, "")
                print(f"    {icon} [{r.compliance_burden}] {r.name} ({r.jurisdiction})")
                print(f"        {r.brief_requirement}")
        if regulatory_out.key_compliance_risks:
            print("\n  Key compliance risks:")
            for risk in regulatory_out.key_compliance_risks:
                print(f"    • {risk}")
        print(f"\n  Summary: {regulatory_out.regulatory_summary}")
        print("\n  → Legal/compliance review required before DFV.")

    # TODO (DFV Agent): gateway — only proceed if ready_for_dfv
    # TODO (DFV Agent): pass refined_idea from tips_out to DFV agent

    if tips_out.ready_for_dfv:
        print("\nResult: Idea qualifies for DFV evaluation.")
    else:
        print("\nResult: Idea does NOT qualify. Address RED scores first.")

    print("\nDone.")


if __name__ == "__main__":
    main()
