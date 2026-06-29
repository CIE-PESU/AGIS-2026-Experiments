# Evaluator Agent

An AI-powered evaluation agent built with CrewAI for automated startup assessment. Evaluates ideas through a structured multi-phase pipeline: Pre-Evaluation, Market Validation, Regulatory Mapping, Ethics Pre-Screen, TIPSC scoring, and Follow-up.

## Pipeline

The evaluation pipeline runs in six sequential phases:

1. **Pre-Evaluation** — Interactive interview (up to 6 turns) to collect: problem statement, customer segment, consequence, assumptions, proposed solution, target geography, and industry sector.
2. **Market Validation** — Web research (Tavily) validating founder assumptions (CONFIRMED/UNCONFIRMED/CONTRADICTED), competitor landscape, and overall validation summary (STRONG/MIXED/WEAK).
3. **Regulatory Mapping** — Identifies applicable regulations (GDPR, HIPAA, DPDP Act, etc.), compliance burden, and whether specialist review is needed.
4. **Ethics Pre-Screen** — Three gates (harm vector, legal risk, problem-solution integrity) flag structural concerns. Ideas with RED on any gate are rejected before scoring.
5. **TIPSC Evaluation** — Scores across Timely, Important, Profitable, Solvable dimensions (GREEN/YELLOW/RED), computes overall readiness (STRONG/MODERATE/WEAK), and determines DFV eligibility.
6. **Follow-up (up to 3 turns)** — Iterative Q&A where the agent asks targeted questions to address RED/YELLOW scores, then re-evaluates TIPSC with new evidence.

## Installation

```bash
pip install -e .
```

Or with `uv`:

```bash
uv sync
```

## Dependencies

- Python >= 3.10
- crewai >= 1.14.6
- langchain-openai >= 0.3.0
- pydantic >= 2.0
- pyyaml >= 6.0
- tavily-python >= 0.7.26

## Project Structure

```
src/
├── config/              # Agent and task configurations
│   ├── agents.yaml      # Agent definitions (6 agents)
│   └── tasks.yaml       # Task definitions (5 tasks)
├── skills/              # Custom skill rubrics
│   ├── preeval/         # Pre-evaluation skill
│   ├── tipsc/           # TIPSC evaluation rubric
│   └── ethics/          # Ethics pre-screen rubric
├── main.py              # Pipeline orchestrator (entry point)
├── models.py            # Pydantic models for all phases
└── __init__.py
outputs/                 # Saved JSON outputs from each phase
```

## Usage

```bash
python -m src.main
```

With `uv`:

```bash
uv run python -m src.main
```

The pipeline is interactive — you will be prompted during Pre-Evaluation and Follow-up phases.

## Configuration

Edit `src/config/agents.yaml` and `src/config/tasks.yaml` to customize agent behavior and evaluation criteria. Rubrics live in `src/skills/*/SKILL.md`.

## Environment Variables

| Variable | Purpose |
|---|---|
| `LM_STUDIO_URL` | LM Studio server URL (default: `http://127.0.0.1:1234/v1`) |
| `OPENAI_API_KEY` | API key (set to `lm-studio` for local) |
| `OPENAI_MODEL_NAME` | Model name (default: `openai/mistralai/mistral-7b-instruct-v0.3`) |
| `TAVILY_API_KEY` | Tavily search API key for market validation & regulatory research |
| `PREEVAL_MAX_TURNS` | Max interview turns (default: 6) |
| `VALIDATION_TIMEOUT_SECS` | Validation research timeout (default: 600) |
| `REGULATORY_TIMEOUT_SECS` | Regulatory research timeout (default: 300) |
