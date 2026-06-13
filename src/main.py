#!/usr/bin/env python3
"""Pre-Eval -> TIPSC pipeline using crewAI with local LLM (LM Studio)."""

import os

os.environ["OPENAI_API_KEY"] = "lm-studio"
os.environ["OPENAI_MODEL_NAME"] = "openai/mistralai/mistral-7b-instruct-v0.3"

import json
import sys
from pathlib import Path

import yaml
from crewai import Agent, Crew, LLM, Process, Task
from crewai_tools import TavilySearchTool
from models import PreEvalOutput, TIPSCOutput, FollowUpOutput

BASE_DIR = Path(__file__).resolve().parent

os.environ["TAVILY_API_KEY"] = ""   # ← paste your key
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


def clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        text = text[brace_start : brace_end + 1]
    return text


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
    base_url = os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1")
    return LLM(
        model="openai/mistralai/mistral-7b-instruct-v0.3",
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
        temperature=0.3,
    )


# ── Phase 1: Pre-Eval conversation loop ────────


def run_preeval(llm: LLM, skill_text: str) -> PreEvalOutput:
    print("\n--- Pre-Evaluation (max 5 exchanges) ---")

    messages = [
        {"role": "system", "content": skill_text},
        {
            "role": "user",
            "content": "Begin the interview. Ask the first question "
                        "to understand the problem.",
        },
    ]

    MAX_TURNS = 5
    turn = 0

    while turn < MAX_TURNS:
        ai_text = llm.call(messages).strip()
        print(f"\n[AI turn {turn + 1}] {ai_text}")

        user_input = input("> ").strip()
        if not user_input:
            user_input = "(skipped)"

        messages.append({"role": "assistant", "content": ai_text})
        messages.append({"role": "user", "content": user_input})
        turn += 1

    # Summarise the conversation into structured JSON
    messages.append({
        "role": "user",
        "content": (
            "Based on our conversation, produce a JSON object with exactly "
            "these keys: problem_statement, customer_segment, consequence, "
            "assumptions, proposed_solution. Return ONLY valid JSON,"
            "no markdown, no extra text."
        ),
    })
    raw = clean_json(llm.call(messages))

    try:
        return PreEvalOutput.model_validate_json(raw)
    except Exception as e:
        print(f"  JSON parse failed: {e}")
        print("  Retrying with stricter prompt...")
        messages.append({
                "role": "user",
                "content": """
            Return ONLY valid JSON with EXACTLY these keys:

            {
                "problem_statement": "",
                "customer_segment": "",
                "consequence": "",
                "assumptions": [],
                "proposed_solution": ""
            }

            No markdown.
            No explanations.
            No extra keys.
            """
            })
        raw2 = clean_json(llm.call(messages))
        return PreEvalOutput.model_validate_json(raw2)


# ── Phase 2: TIPSC crew evaluation ─────────────


def run_tipsc(
    llm: LLM,
    preeval: PreEvalOutput,
    agents_cfg: dict,
    task_cfg: dict,
    rubric: str,
    followup_context="",
) -> TIPSCOutput:
    agent = Agent(
        role=agents_cfg["tipsc_agent"]["role"],
        goal=agents_cfg["tipsc_agent"]["goal"],
        backstory=agents_cfg["tipsc_agent"]["backstory"],
        llm=llm,
        tools=[search_tool],    # ← Tavily added here
    )

    task = Task(
        description=task_cfg["tipsc_task"]["description"].format(
            tipsc_rubric=rubric,
            preeval_json=preeval.model_dump_json(indent=2),
            followup_context=followup_context,
        ),
        expected_output=task_cfg["tipsc_task"]["expected_output"],
        agent=agent,
        )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    if result.pydantic:
        return result.pydantic

    raw = clean_json(result.raw)
    try:
        return TIPSCOutput.model_validate_json(raw)
    except Exception as e:
        print(f"ERROR: Could not parse TIPSC output: {e}")
        print("Raw output:")
        print(result.raw)
        raise

def parse_pydantic_result(result, model):
    if result.pydantic:
        return result.pydantic

    raw = clean_json(result.raw)
    return model.model_validate_json(raw)

def run_followup(
    llm,
    tipsc_output,
    agents_cfg,
    task_cfg,
):
    agent = Agent(
        role=agents_cfg["followup_agent"]["role"],
        goal=agents_cfg["followup_agent"]["goal"],
        backstory=agents_cfg["followup_agent"]["backstory"],
        llm=llm,
    )

    task = Task(
        description=task_cfg["followup_task"]["description"].format(
            tipsc_json=tipsc_output.model_dump_json(indent=2)
        ),
        expected_output=task_cfg["followup_task"]["expected_output"],
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    return parse_pydantic_result(
        result,
        FollowUpOutput,
    )


# ── Entry point ────────────────────────────────


def main():
    agents_cfg = load_yaml("config/agents.yaml")
    task_cfg = load_yaml("config/tasks.yaml")
    preeval_skill = load_text("skills/preeval/SKILL.md")
    tipsc_rubric = load_text("skills/tipsc/SKILL.md")

    # Quick connectivity check
    try:
        llm = load_llm()
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
    preeval_out = run_preeval(llm, preeval_skill)
    save_json(preeval_out.model_dump(), "preeval_output.json")

    print("\n" + "=" * 60)
    print("PHASE 2: TIPSC Evaluation")
    print("=" * 60)
    tips_out = run_tipsc(llm, preeval_out, agents_cfg, task_cfg, tipsc_rubric)
    save_json(tips_out.model_dump(), "tipsc_output.json")

    followup = run_followup(
    llm,
    tips_out,
    agents_cfg,
    task_cfg,
    )

    if followup.needs_followup:

        question = followup.questions[0]

        print("\n" + "=" * 60)
        print("FOLLOW-UP QUESTION")
        print("=" * 60)

        print(question)

        answer = input("> ").strip()

        followup_context = f"""
        Follow-up Question:
        {question}

        Founder Answer:
        {answer}
        """

        print("\nRe-evaluating TIPSC...\n")

        tips_out = run_tipsc(
            llm,
            preeval_out,
            agents_cfg,
            task_cfg,
            tipsc_rubric,
            followup_context=followup_context,
        )



    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  Scores:          {tips_out.tips_rag_scores}")
    print(f"  Readiness:       {tips_out.overall_readiness}")
    print(f"  Ready for DFV:   {tips_out.ready_for_dfv}")
    for dim, note in tips_out.tips_coaching.items():
        if note:
            print(f"  Coaching [{dim}]: {note}")

    # TODO (DFV Agent): gateway — only proceed if ready_for_dfv
    # TODO (DFV Agent): pass refined_idea from tips_out to DFV agent
    if tips_out.ready_for_dfv:
        print("\nResult: Idea qualifies for DFV evaluation.")
    else:
        print("\nResult: Idea does NOT qualify. Address RED scores first.")

    print("Done.")


if __name__ == "__main__":
    main()
