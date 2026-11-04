#!/usr/bin/env python3
"""Quickstart Agent - Lite evaluation: Ethics + TIPSC + DFV in one rapid assessment."""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env", encoding="utf-8-sig")

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import yaml
from crewai import LLM, Agent, Crew, Process, Task
from crewai.skills import activate_skill, discover_skills
from crewai_tools import SerperDevTool, TavilySearchTool

from quickstart_agent.models import QuickstartInput, QuickstartOutput

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

tavily_tool = TavilySearchTool(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None
serper_tool = SerperDevTool(api_key=SERPER_API_KEY) if SERPER_API_KEY else None

llm = LLM(
    model=os.environ["OPENAI_MODEL_NAME"],
    base_url=os.environ["LM_STUDIO_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
    temperature=0.1,
    # Skip reasoning tokens for the speed-focused NVIDIA model.
    extra_body=(
        {"chat_template_kwargs": {"enable_thinking": False}}
        if os.environ["OPENAI_MODEL_NAME"].endswith("nemotron-3.5-lightning-30b-a3b")
        else {}
    ),
    timeout=float(os.getenv("CREWAI_TIMEOUT_SECONDS", "600")),
    max_tokens=int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "4096")),
)


# Discover and activate local business framework guidelines.
skills = discover_skills(Path(__file__).parent / "skills")
activated = [activate_skill(s) for s in skills]
if [s.name for s in activated] != ["quickstart-skill"]:
    raise ValueError(
        "Local skills are missing or their order changed; check agent skill assignments."
    )


def load_yaml(rel: str) -> dict:
    path = Path(__file__).parent / "config" / rel
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_crew():
    agents_cfg = load_yaml("agents.yaml")
    tasks_cfg = load_yaml("tasks.yaml")

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
        skills=[activated[0]],
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
    """Extract one complete JSON object without swallowing trailing model prose."""
    raw = raw.strip()
    if raw.startswith("["):
        return raw
    decoder = json.JSONDecoder()
    for pos, char in enumerate(raw):
        if char == "{":
            try:
                value, length = decoder.raw_decode(raw[pos:])
            except ValueError:
                if pos == 0:
                    return raw
                continue
            if isinstance(value, dict):
                return raw[pos : pos + length]
    return raw.strip()


def _parse_result(input_data: QuickstartInput, result) -> QuickstartOutput:
    raw = getattr(result, "raw", "") or ""
    cleaned = _extract_json_block(raw)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("Quickstart agent returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Quickstart agent output must be an object")
    return QuickstartOutput.from_raw(
        input_data,
        parsed.get("parameters", []),
        parsed.get("parameter_advice", {}),
        parsed.get("priority_advice", []),
    )


def run_quickstart_eval(input_data: QuickstartInput) -> QuickstartOutput:
    """Synchronous version for CLI usage."""
    result = create_crew().kickoff(inputs=input_data.model_dump())
    return _parse_result(input_data, result)


async def run_quickstart_eval_async(input_data: QuickstartInput) -> QuickstartOutput:
    """Async version for FastAPI usage."""
    result = await create_crew().kickoff_async(inputs=input_data.model_dump())
    return _parse_result(input_data, result)


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
    print("  QUICKSTART EVALUATION RESULTS")
    print("=" * 70)

    print(
        f"\n  Summary: {RATING_COLORS['GREEN']}GREEN: {output.green_count}{RATING_COLORS['RESET']}  "
        f"{RATING_COLORS['YELLOW']}YELLOW: {output.yellow_count}{RATING_COLORS['RESET']}  "
        f"{RATING_COLORS['RED']}RED: {output.red_count}{RATING_COLORS['RESET']}\n"
    )

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
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
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
        lines = content.split("\n")
        # Handle case where first line is a choice ("1" or "2") and second is JSON
        if len(lines) >= 2 and lines[0] in ("1", "2"):
            data = json.loads(lines[1])
        else:
            data = json.loads(content)
        return QuickstartInput(**data)
    except Exception as exc:
        raise ValueError("Piped Quickstart input was invalid; evaluation was not started.") from exc


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
            print("   uv run python dev.py")
            print("\n   Or via backend API: POST /api/v1/sessions (authenticated founder intake)")
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
        print("   uv run python dev.py")
    else:
        print("\n✅ Quickstart evaluation complete.")


if __name__ == "__main__":
    main()
