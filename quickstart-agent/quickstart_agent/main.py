#!/usr/bin/env python3
"""Quickstart Agent - Lite evaluation: Ethics + TIPSC + DFV in one rapid assessment."""

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import litellm
litellm.drop_params = True

_original_litellm_completion = litellm.completion
_original_litellm_acompletion = litellm.acompletion


def _sanitize_tool_choice(kwargs):
    tool_choice = kwargs.get("tool_choice")
    if isinstance(tool_choice, dict):
        tc_type = tool_choice.get("type")
        kwargs["tool_choice"] = "required" if tc_type in ("function", "tool") else "auto"
    return kwargs


def _patched_litellm_completion(*args, **kwargs):
    kwargs = _sanitize_tool_choice(kwargs)
    max_retries = 3
    for attempt in range(max_retries):
        res = _original_litellm_completion(*args, **kwargs)
        if res and hasattr(res, "choices") and len(res.choices) > 0:
            msg = res.choices[0].message
            content = getattr(msg, "content", None)
            tool_calls = getattr(msg, "tool_calls", None)
            if content or tool_calls:
                return res
            if attempt < max_retries - 1:
                continue
        return res
    return res


async def _patched_litellm_acompletion(*args, **kwargs):
    kwargs = _sanitize_tool_choice(kwargs)
    max_retries = 3
    for attempt in range(max_retries):
        res = await _original_litellm_acompletion(*args, **kwargs)
        if res and hasattr(res, "choices") and len(res.choices) > 0:
            msg = res.choices[0].message
            content = getattr(msg, "content", None)
            tool_calls = getattr(msg, "tool_calls", None)
            if content or tool_calls:
                return res
            if attempt < max_retries - 1:
                continue
        return res
    return res


litellm.completion = _patched_litellm_completion
litellm.acompletion = _patched_litellm_acompletion

import yaml
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import TavilySearchTool, SerperDevTool

from quickstart_agent.models import QuickstartInput, QuickstartOutput, ParameterRating

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

tavily_tool = TavilySearchTool(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None
serper_tool = SerperDevTool(api_key=SERPER_API_KEY) if SERPER_API_KEY else None

llm = LLM(
    model=os.environ["OPENAI_MODEL_NAME"],
    base_url=os.environ["LM_STUDIO_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
    temperature=0.1,
    timeout=108000,
)


def load_skill() -> str:
    skill_path = Path(__file__).parent / "skills" / "QUICKSTART_SKILL.md"
    with open(skill_path, encoding="utf-8") as f:
        return f.read()


def load_yaml(rel: str) -> dict:
    path = Path(__file__).parent / "config" / rel
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_crew():
    agents_cfg = load_yaml("agents.yaml")
    tasks_cfg = load_yaml("tasks.yaml")
    skill_text = load_skill()

    agent_cfg = agents_cfg["quickstart_evaluator"]
    task_cfg = tasks_cfg["evaluate_idea"]

    tools = []
    if tavily_tool:
        tools.append(tavily_tool)
    if serper_tool:
        tools.append(serper_tool)

    agent = Agent(
        role=agent_cfg["role"],
        goal=agent_cfg["goal"],
        backstory=agent_cfg["backstory"],
        llm=llm,
        tools=tools,
        verbose=agent_cfg.get("verbose", False),
        max_iter=agent_cfg.get("max_iter", 3),
    )

    task = Task(
        description=task_cfg["description"],
        expected_output=task_cfg["expected_output"],
        agent=agent,
        async_execution=task_cfg.get("async_execution", False),
    )

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


def _extract_json_block(raw: str) -> str:
    if not raw:
        return ""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE | re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and start < end:
            cleaned = cleaned[start:end + 1]
    return cleaned


def run_quickstart_eval(input_data: QuickstartInput) -> QuickstartOutput:
    """Synchronous version for CLI usage."""
    crew = create_crew()
    result = crew.kickoff(inputs=input_data.model_dump())

    raw_val = getattr(result, "raw", "") or ""
    cleaned = _extract_json_block(raw_val)

    if not cleaned or not cleaned.startswith("{"):
        raise ValueError(
            f"Agent returned empty or non-JSON output.\nRaw: {repr(raw_val[:500])}"
        )

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse failed: {exc}\nCleaned: {repr(cleaned[:500])}")

    params = parsed.get("parameters", [])
    advice = parsed.get("parameter_advice", {})
    priority = parsed.get("priority_advice", [])

    if len(params) != 10:
        raise ValueError(f"Expected 10 parameters, got {len(params)}")

    return QuickstartOutput.from_raw(input_data, params, advice, priority)


async def run_quickstart_eval_async(input_data: QuickstartInput) -> QuickstartOutput:
    """Async version for FastAPI usage."""
    crew = create_crew()
    result = await crew.kickoff_async(inputs=input_data.model_dump())

    raw_val = getattr(result, "raw", "") or ""
    cleaned = _extract_json_block(raw_val)

    if not cleaned or not cleaned.startswith("{"):
        raise ValueError(
            f"Agent returned empty or non-JSON output.\nRaw: {repr(raw_val[:500])}"
        )

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse failed: {exc}\nCleaned: {repr(cleaned[:500])}")

    params = parsed.get("parameters", [])
    advice = parsed.get("parameter_advice", {})
    priority = parsed.get("priority_advice", [])

    if len(params) != 10:
        raise ValueError(f"Expected 10 parameters, got {len(params)}")

    return QuickstartOutput.from_raw(input_data, params, advice, priority)


def print_banner():
    print("\n" + "=" * 60)
    print("  QUICKSTART AGENT - Rapid Startup Evaluation")
    print("  Ethics (3) + TIPSC (4) + DFV (3) = 10 Parameters")
    print("=" * 60 + "\n")


def select_path() -> str:
    print("Choose your path:")
    print("  1. Start Building  → Full pipeline (TIPSC → DFV)")
    print("  2. Idea in Running → Quick evaluation (this agent)")
    while True:
        choice = input("\nEnter 1 or 2: ").strip()
        if choice in ("1", "2"):
            return choice
        print("Invalid. Enter 1 or 2.")


def ask_7_questions() -> QuickstartInput:
    questions = [
        ("problem", "What is the core problem you're solving?"),
        ("customer", "Who specifically experiences this problem?"),
        ("solution", "What is your proposed solution?"),
        ("consequence", "What happens if this problem isn't solved?"),
        ("business_model", "How will this make money? Who pays?"),
        ("urgency", "Why is now the right time? (timeline/urgency)"),
        ("hurdles", "What are the biggest technical, legal, or regulatory hurdles?"),
    ]

    answers = {}
    print("\n" + "-" * 60)
    print("QUICKSTART EVALUATION - Answer 7 Questions")
    print("-" * 60 + "\n")

    for key, q in questions:
        while True:
            ans = input(f"{q}\n> ").strip()
            if ans:
                answers[key] = ans
                print()
                break
            print("This field is required. Please provide an answer.\n")

    return QuickstartInput(**answers)


RATING_COLORS = {
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

PARAM_LABELS = {
    "harm_vector": "Harm Vector (Ethics)",
    "legal_risk": "Legal Risk (Ethics)",
    "problem_solution_integrity": "Problem-Solution Integrity (Ethics)",
    "timely": "Timely (TIPSC)",
    "important": "Important (TIPSC)",
    "profitable": "Profitable (TIPSC)",
    "solvable": "Solvable (TIPSC)",
    "desirability": "Desirability (DFV)",
    "feasibility": "Feasibility (DFV)",
    "viability": "Viability (DFV)",
}


def print_pretty_table(output: QuickstartOutput):
    print("\n" + "=" * 70)
    print(f"  QUICKSTART EVALUATION RESULTS")
    print("=" * 70)

    print(f"\n  Summary: {RATING_COLORS['GREEN']}GREEN: {output.green_count}{RATING_COLORS['RESET']}  "
          f"{RATING_COLORS['YELLOW']}YELLOW: {output.yellow_count}{RATING_COLORS['RESET']}  "
          f"{RATING_COLORS['RED']}RED: {output.red_count}{RATING_COLORS['RESET']}\n")

    print(f"  {'Parameter':<38} {'Rating':<8} Reason")
    print("  " + "-" * 68)

    for p in output.parameters:
        color = RATING_COLORS.get(p.rating, "")
        reset = RATING_COLORS["RESET"]
        label = PARAM_LABELS.get(p.name, p.name)
        print(f"  {label:<38} {color}{p.rating:<8}{reset} {p.reason}")

    print("\n" + "=" * 70)
    print("  STARTUP ADVICE")
    print("=" * 70)

    has_advice = False
    for p in output.parameters:
        adv = output.parameter_advice.get(p.name, "")
        if adv:
            has_advice = True
            color = RATING_COLORS.get(p.rating, "")
            reset = RATING_COLORS["RESET"]
            label = PARAM_LABELS.get(p.name, p.name)
            print(f"\n  {color}{label} ({p.rating}){reset}")
            print(f"    → {adv}")

    if not has_advice:
        print("\n  All parameters GREEN — no specific advice needed.")

    print("\n" + "-" * 70)
    print("  PRIORITY NEXT STEPS")
    print("-" * 70)
    for i, step in enumerate(output.priority_advice, 1):
        print(f"  {i}. {step}")

    print("\n" + "=" * 70 + "\n")


def print_json(output: QuickstartOutput):
    print(json.dumps(output.model_dump(), indent=2))


def save_json(output: QuickstartOutput):
    out_dir = Path(__file__).parent.parent / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"quickstart_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output.model_dump(), f, indent=2, default=str)
    print(f"  Saved: {path}")


def read_stdin_input() -> QuickstartInput | None:
    """Read QuickstartInput from stdin if available (for API mode)."""
    if sys.stdin.isatty():
        return None
    try:
        content = sys.stdin.read().strip()
        if not content:
            return None
        lines = content.split('\n')
        # Handle case where first line is a choice ("1" or "2") and second is JSON
        if len(lines) >= 2 and lines[0] in ("1", "2"):
            data = json.loads(lines[1])
        else:
            data = json.loads(content)
        return QuickstartInput(**data)
    except Exception:
        return None


def main():
    print_banner()
    
    # Check for stdin input (API mode)
    stdin_input = read_stdin_input()
    if stdin_input:
        input_data = stdin_input
    else:
        # Interactive CLI mode
        choice = select_path()

        if choice == "1":
            print("\n🚀 Launching full pipeline...")
            print("   Run this from project root:")
            print("   cd TIPSC-Agent && uv run python -m src.main")
            print("\n   Or via backend API: POST /api/v1/sessions/{id}/start-flow")
            return

        input_data = ask_7_questions()

    print("Evaluating...\n")
    try:
        result = run_quickstart_eval(input_data)
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        sys.exit(1)

    # API mode: only output JSON to stdout
    if stdin_input:
        print_json(result)
        return

    # CLI mode: pretty output + JSON + save
    print_pretty_table(result)
    print_json(result)
    save_json(result)

    proceed = input("Proceed to full pipeline (TIPSC → DFV)? [y/N]: ").strip().lower()
    if proceed == "y":
        print("\n🚀 Run full pipeline:")
        print("   cd ../TIPSC-Agent && uv run python -m src.main")
    else:
        print("\n✅ Quickstart evaluation complete.")


if __name__ == "__main__":
    main()