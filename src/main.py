#!/usr/bin/env python3
"""Pre-Eval -> TIPSC pipeline using crewAI with local LLM (LM Studio)."""

import os,re

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


def clean_json(text: str) -> str:
    text = text.strip()
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text.strip())
    text = text.strip()
    # Extract first complete JSON object using depth tracking
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                return text[start:i+1]
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
        temperature=0.2,
    )

JSON_SYSTEM_PREFIX = (
    "You are a JSON-only output machine. "
    "You MUST respond with a single valid JSON object and nothing else. "
    "No markdown. No code fences. No explanation. No preamble. No trailing text. "
    "Your entire response is parsed directly by json.loads(). "
    "If you add anything outside the JSON object, the system will crash. "
    "Start your response with { and end it with }."
)
 
def call_llm_for_json(llm: LLM, messages: list) -> str:
    """
    Prepend the JSON enforcement system message to any direct llm.call() invocation
    that expects a JSON response. This replaces response_format={"type":"json_object"}.
    """
    enforced = [{"role": "system", "content": JSON_SYSTEM_PREFIX}] + messages
    return llm.call(enforced).strip()
 

# ── Phase 1: Pre-Eval conversation loop ────────


def run_preeval(llm: LLM, skill_text: str) -> PreEvalOutput:
    print("\n--- Pre-Evaluation (max 5 exchanges) ---")

    MAX_TURNS = int(os.environ.get("PREEVAL_MAX_TURNS", 5))

    messages = [
        {"role": "system", "content": skill_text},
        {
            "role": "user",
            "content": ("Begin the interview. Ask the first question "
                        "to understand the problem."),
        },
    ]

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
    summary_prompt = (
        "The interview is complete. "
        "Summarise the conversation into this exact JSON object. "
        "Fill every field from the answers given. "
        "assumptions must be a JSON array of strings. "
        "Output the JSON object only — no other text.\n\n"
        "{\n"
        '  "problem_statement": "one sentence describing the core problem",\n'
        '  "customer_segment": "who experiences the problem",\n'
        '  "consequence": "what happens if unsolved",\n'
        '  "assumptions": ["assumption 1", "assumption 2"],\n'
        '  "proposed_solution": "what the team plans to build"\n'
        "}"
    )

    summary_messages = messages + [{"role": "user","content": summary_prompt}]
    raw = clean_json(call_llm_for_json(llm,summary_messages))

    try:
        return PreEvalOutput.model_validate_json(raw)
    except Exception as e:
        print(f"  JSON parse failed: {e}\n  Retrying with stricter prompt...")
        retry_prompt = (
            "Your previous response was not valid JSON. "
            "Output ONLY this object, with no other characters before or after:\n\n"
            "{\n"
            '  "problem_statement": "...",\n'
            '  "customer_segment": "...",\n'
            '  "consequence": "...",\n'
            '  "assumptions": ["..."],\n'
            '  "proposed_solution": "..."\n'
            "}"
        )
        retry_messages = summary_messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": retry_prompt},
        ]
        raw2 = clean_json(call_llm_for_json(llm, retry_messages))
        return PreEvalOutput.model_validate_json(raw2)


# ── Phase 2: TIPSC crew evaluation ─────────────


def run_tipsc(
    llm: LLM,
    preeval: PreEvalOutput,
    agents_cfg: dict,
    task_cfg: dict,
    rubric: str,
    followup_context: str = "",
) -> TIPSCOutput:
    agent = Agent(
        role=agents_cfg["tipsc_agent"]["role"],
        goal=agents_cfg["tipsc_agent"]["goal"],
        backstory=agents_cfg["tipsc_agent"]["backstory"],
        llm=llm,
    )

    task = Task(
        description=task_cfg["tipsc_task"]["description"].format(
            tipsc_rubric=rubric,
            preeval_json=preeval.model_dump_json(indent=2),
            followup_context=followup_context if followup_context else "None provided.",
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

    try:
        return parse_pydantic_result(result, TIPSCOutput)
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
    llm: LLM,
    tipsc_output: TIPSCOutput,
    agents_cfg: dict,
    task_cfg: dict,
    followup_context: str = "",  # FIX: pass accumulated prior Q&A
) -> FollowUpOutput:
    agent = Agent(
        role=agents_cfg["followup_agent"]["role"],
        goal=agents_cfg["followup_agent"]["goal"],
        backstory=agents_cfg["followup_agent"]["backstory"],
        llm=llm,
    )

    task = Task(
        description=task_cfg["followup_task"]["description"].format(
            tipsc_json=tipsc_output.model_dump_json(indent=2),
            followup_context=followup_context if followup_context else "None yet.",
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

    llm=load_llm()

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
    preeval_out = run_preeval(llm, preeval_skill)
    save_json(preeval_out.model_dump(), "preeval_output.json")

    print("\n" + "=" * 60)
    print("PHASE 2: TIPSC Evaluation")
    print("=" * 60)
    tips_out = run_tipsc(llm, preeval_out, agents_cfg, task_cfg, tipsc_rubric)
    save_json(tips_out.model_dump(), "tipsc_output.json")

    MAX_FOLLOWUP_TURNS = 3
    followup_context= ""

    for turn in range(MAX_FOLLOWUP_TURNS):

        followup = run_followup(
        llm,
        tips_out,
        agents_cfg,
        task_cfg,
        followup_context=followup_context,
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
            followup_context=followup_context,
        )

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

    # TODO (DFV Agent): gateway — only proceed if ready_for_dfv
    # TODO (DFV Agent): pass refined_idea from tips_out to DFV agent

    if tips_out.ready_for_dfv:
        print("\nResult: Idea qualifies for DFV evaluation.")
    else:
        print("\nResult: Idea does NOT qualify. Address RED scores first.")

    print("\nDone.")


if __name__ == "__main__":
    main()
