"""
Entrepreneurial Opportunity Validation System — CrewAI Memory Variant
=====================================================================

  memory=True is passed to every Crew instance in run_agent().

This enables CrewAI's built-in memory stack:
  - Short-term memory  : RAG over recent interactions (ChromaDB)
  - Long-term memory   : cross-run persistence (SQLite)
  - Entity memory      : tracks key nouns/concepts across turns

Requires: pip install sentence-transformers

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AGENT 1 — Opportunity Evaluation Agent
  Phase 1a: TIPSC Triage (first-pass: Strong / Weak / Unclear)
  Phase 1b: TIPSC Deep-Dive (one criterion at a time)
  Phase 1c: Need Validation
  Phase 1d: COP (inferred organically throughout)

AGENT 2 — Idea Evaluation Agent
  Phase 2a: PSEA Evaluation (initial pass)
  Phase 2b: Refinement Loop (until READY_FOR_DFV)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Workflow:
  Problem Input
    → Opportunity Evaluation (TIPSC → Need → COP)
    → [APPROVED] → Solution Input
    → Idea Evaluation (PSEA + Feasibility)
    → [READY_FOR_DFV]
"""

import os
import sys
from pathlib import Path

import requests
import yaml
from datetime import datetime
from typing import List
from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process, LLM
from crewai.flow.flow import Flow, listen, start
from crewai_tools import SerperDevTool


# ══════════════════════════════════════════════════════════════
# LOAD CONFIGURATION & PROMPTS
# ══════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent


def _load_yaml(rel_path: str) -> dict:
    """Load and return a YAML file relative to the project root."""
    with open(BASE_DIR / rel_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


cfg      = _load_yaml("config/settings.yaml")
opp_p    = _load_yaml("prompts/opportunity_agent.yaml")
idea_p   = _load_yaml("prompts/idea_agent.yaml")
ui       = _load_yaml("prompts/ui_strings.yaml")

# ── Convenience accessors ──────────────────────────────────────
_val     = cfg["validation"]
_conv    = cfg["conversation"]
_search  = cfg["search"]
_display = cfg["display"]

MAX_TURNS_PER_CRITERION = _val["max_turns_per_criterion"]
W                       = _display["console_width"]


# ══════════════════════════════════════════════════════════════
# CONFIGURATION — LLM & SEARCH
# ══════════════════════════════════════════════════════════════

llm_cfg = cfg["llm"]
llm = LLM(
    model=llm_cfg["model"],
    base_url=llm_cfg["base_url"],
    api_key=llm_cfg["api_key"],
)

agent_tools = [SerperDevTool()]

# Serper web search — Python-direct (no agent tool calls).
# Search results are pre-fetched in Python and injected as context
# into each task description.  Small LLMs cannot reliably trigger
# function/tool calls; pre-fetching bypasses that entirely.
#
# Free key (2,500 searches/month): https://serper.dev
# Set before running:  export SERPER_API_KEY=your_key_here
_serper_key = (
    os.environ.get("SERPER_API_KEY")
    or _search.get("serper_api_key", "")
)
_search_on = bool(_serper_key)

if _search_on:
    print(ui["startup"]["search_enabled"])
else:
    print(ui["startup"]["search_disabled"])


# ══════════════════════════════════════════════════════════════
# STATE MODEL
# ══════════════════════════════════════════════════════════════

class ValidationState(BaseModel):
    problem:  str = ""
    solution: str = ""

    # Separate conversation histories per agent
    opp_history:  List[dict] = []   # {"role": "agent"|"user", "content": str}
    idea_history: List[dict] = []

    # Opportunity evaluation state
    opp_status:        str  = "PENDING"   # PENDING → IN_PROGRESS → APPROVED
    opp_report:        str  = ""
    opp_last_q:        str  = ""          # Tracks last question to detect repetition
    criterion_turns:   dict = {}          # {"I": 3, "P": 1, ...} turns spent per criterion
    current_criterion: str  = ""          # Letter currently under investigation

    # Idea evaluation state
    idea_status: str = "PENDING"          # PENDING → IN_PROGRESS → READY_FOR_DFV
    idea_report: str = ""
    idea_last_q: str = ""                 # Tracks last question to detect repetition


# ══════════════════════════════════════════════════════════════
# CLI UTILITIES
# ══════════════════════════════════════════════════════════════

def hr(char: str = "=") -> None:
    """Print a horizontal rule."""
    print(char * W)


def section(title: str) -> None:
    """Print a bold section header."""
    print()
    hr()
    pad = max(0, (W - len(title) - 2) // 2)
    print(" " * pad + title)
    hr()
    print()


def extract_displayed_question(text: str) -> str:
    """
    Pull the question the agent is asking out of any response format.

    The model (especially small LLMs) does not always follow the structured
    template. This function tries multiple fallback strategies so there is
    always something concrete shown to the user.

    Strategy 1 — Explicit QUESTION: section (expected format).
    Strategy 2 — Last line in the response that ends with '?'.
    Strategy 3 — Substring around the last '?' anywhere in the text.
    Strategy 4 — Generic fallback.
    """
    # Strategy 1: look for the QUESTION: marker we ask the model to include
    if "QUESTION:" in text.upper():
        idx   = text.upper().rfind("QUESTION:")   # rfind → take the last one
        chunk = text[idx + len("QUESTION:"):].strip()
        line  = chunk.split("\n")[0].strip()
        if len(line) > 5:
            return line

    # Strategy 2: last non-empty line that ends with a '?'
    for line in reversed(text.strip().split("\n")):
        line = line.strip()
        if line.endswith("?") and len(line) > 10:
            return line

    # Strategy 3: substring from last sentence boundary to last '?'
    if "?" in text:
        last_q  = text.rfind("?")
        before  = text[:last_q]
        start   = max(before.rfind("."), before.rfind(":"), before.rfind("\n"))
        fragment = text[start + 1: last_q + 1].strip()
        if len(fragment) > 10:
            return fragment

    # Strategy 4: generic fallback from UI strings
    return ui["agent_display"]["fallback_question"]


def _wrap(text: str, width: int = W - 4) -> List[str]:
    """Word-wrap a string to a given width and return a list of lines."""
    words, lines, cur = text.split(), [], ""
    for word in words:
        if len(cur) + len(word) + 1 <= width:
            cur = (cur + " " + word).strip()
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def agent_says(text: str) -> None:
    """
    Print the agent's response then always render the question in its own
    clearly labelled block — so the user never has to hunt for what to answer.

    Works regardless of whether the model followed the structured template.
    """
    question = extract_displayed_question(text)
    label    = ui["agent_display"]["asking_label"]

    # Full agent response
    print()
    hr("-")
    print(text.strip())
    hr("-")

    # Question callout — always shown below
    print()
    print("=" * W)
    print(f"  {label}")
    print("=" * W)
    for line in _wrap(question):
        print(f"  {line}")
    print("=" * W)
    print()


def ask(prompt: str = "") -> str:
    """Prompt the user for input and return the trimmed response."""
    if prompt:
        print(f"\n  {prompt}")
    response = input("\n  > ").strip()
    print()
    return response


def format_history(history: List[dict]) -> str:
    """
    Build a minimal context block for the agent — NOT a full transcript.

    Instead of dumping every turn, we extract only:
      - Resolved criterion verdicts (scraped from agent responses)
      - The last N Q&A pairs (enough for the model to stay oriented)

    This keeps the prompt small for smaller LLMs while preserving
    the state the agent actually needs to make a good decision.
    """
    if not history:
        return "(No prior conversation.)"

    # ── 1. Scrape resolved verdicts from all agent turns ──────
    verdict_lines = []
    for turn in history:
        if turn["role"] != "agent":
            continue
        text = turn["content"]
        # Look for lines like "T — Timely: Strong — ..."
        for line in text.split("\n"):
            l = line.strip()
            if any(l.startswith(f"{c} —") or l.startswith(f"{c}:") for c in "TIPSCN"):
                if any(w in l.upper() for w in ("STRONG", "WEAK", "ACCEPTED", "UNCLEAR", "CONFIRMED", "RESOLVED")):
                    verdict_lines.append(f"  {l}")

    # ── 2. Keep only the last 2 Q&A pairs ─────────────────────
    qa_pairs = []
    i = len(history) - 1
    while i >= 0 and len(qa_pairs) < 2:
        if history[i]["role"] == "user":
            answer = history[i]["content"]
            # Find the question that preceded it
            for j in range(i - 1, -1, -1):
                if history[j]["role"] == "agent":
                    q_text = history[j]["content"]
                    if "QUESTION:" in q_text.upper():
                        q_start = q_text.upper().find("QUESTION:")
                        question = q_text[q_start + len("QUESTION:"):].strip().split("\n")[0].strip()
                    else:
                        question = q_text.strip()[:200]
                    qa_pairs.insert(0, f"Q: {question}\nA: {answer}")
                    i = j - 1
                    break
            else:
                i -= 1
        else:
            i -= 1

    # ── 3. Assemble ───────────────────────────────────────────
    parts = []
    if verdict_lines:
        seen = list(dict.fromkeys(verdict_lines))   # deduplicate, preserve order
        parts.append("RESOLVED SO FAR:\n" + "\n".join(seen))
    if qa_pairs:
        parts.append("RECENT EXCHANGES:\n" + "\n\n".join(qa_pairs))

    return "\n\n".join(parts) if parts else "(No prior conversation.)"


def run_agent(task: Task, agent: Agent) -> str:
    """
    Run a single-agent crew and return a clean plain-text string.

    memory=True enables CrewAI's built-in memory stack:
      - Short-term: RAG over interactions within this session (ChromaDB)
      - Long-term:  SQLite persistence across runs
      - Entity:     tracks key concepts/nouns mentioned

    sentence-transformers is used as the embedder so no OpenAI key is required.
    Install with: pip install sentence-transformers
    """
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        memory=True,
        embedder={
            "provider": "sentence-transformer",
            "config": {
                "model": "all-MiniLM-L6-v2",
            }
        },
    )
    raw = str(crew.kickoff())
    return clean_agent_output(raw)


# Section headers that always mark the START of the agent's formatted response.
# Everything in the string before the first matching header is noise
# (Serper JSON, chain-of-thought, tool call traces) and gets discarded.
_RESPONSE_MARKERS = [
    "TIPSC TRIAGE:",
    "SEARCH FINDINGS:",
    "PSEA EVALUATION:",
    "FEEDBACK:",
    "STATUS: APPROVED",
    "STATUS: NEEDS_MORE_INFO",
    "VERDICT: READY_FOR_DFV",
    "VERDICT: NEEDS_REFINEMENT",
]


def clean_agent_output(text: str) -> str:
    """
    Strip tool-call noise from a raw CrewAI agent output string.

    Strategy:
      1. Scan for the earliest occurrence of any known structured section header.
      2. Return the text from that point onward (the actual formatted response).
      3. Fallback A: if the model used ReAct format, extract after 'Final Answer:'.
      4. Fallback B: return the raw text stripped of leading/trailing whitespace.

    This is deliberately defensive — if none of the heuristics match we still
    return something rather than crashing.
    """
    text_upper = text.upper()
    earliest   = len(text)

    for marker in _RESPONSE_MARKERS:
        idx = text_upper.find(marker.upper())
        if 0 <= idx < earliest:
            earliest = idx

    if earliest < len(text):
        return text[earliest:].strip()

    # Fallback A — ReAct agents sometimes emit "Final Answer: ..."
    if "FINAL ANSWER:" in text_upper:
        idx = text_upper.find("FINAL ANSWER:")
        return text[idx + len("FINAL ANSWER:"):].strip()

    # Fallback B — nothing matched; return stripped raw text
    return text.strip()


def last_exchange(history: List[dict]) -> tuple[str, str]:
    """
    Extract the most recent (agent_question, user_answer) pair from history.
    Returns ("(none)", "(none)") if there isn't a complete pair yet.
    Small LLMs forget context easily — passing these explicitly and prominently
    is more reliable than relying on them reading through the full transcript.
    """
    last_q = "(none)"
    last_a = "(none)"
    for turn in reversed(history):
        if turn["role"] == "user" and last_a == "(none)":
            last_a = turn["content"]
        elif turn["role"] == "agent" and last_q == "(none)" and last_a != "(none)":
            content = turn["content"]
            if "QUESTION:" in content.upper():
                q_start = content.upper().find("QUESTION:")
                last_q  = content[q_start + len("QUESTION:"):].strip().split("\n")[0].strip()
            else:
                last_q = content
            break
    return last_q, last_a


def extract_question(text: str) -> str:
    """Pull the QUESTION: value out of a response for repetition tracking."""
    if "QUESTION:" in text.upper():
        idx = text.upper().find("QUESTION:")
        return text[idx + len("QUESTION:"):].strip().split("\n")[0].strip()
    return text.strip()[:200]   # fallback: first 200 chars


def repetition_warning(last_q: str, current_q: str) -> str:
    """
    If the new question is suspiciously similar to the last one, return an
    injected warning to include in the next prompt. Otherwise empty string.
    Similarity is measured by word overlap.
    """
    if not last_q or last_q == "(none)":
        return ""
    lq_words = set(last_q.lower().split())
    cq_words = set(current_q.lower().split())
    if not lq_words:
        return ""
    overlap = len(lq_words & cq_words) / len(lq_words)
    if overlap > 0.7:
        return ui["prompts"].get(
            "repetition_warning",
            ui["repetition_warning"],
        )
    return ""


def opp_approved(text: str) -> bool:
    """Case-insensitive check for opportunity approval signal."""
    return "STATUS: APPROVED" in text.upper()


def idea_ready(text: str) -> bool:
    """Case-insensitive check for idea readiness signal."""
    return "VERDICT: READY_FOR_DFV" in text.upper()


def parse_criterion(text: str) -> str:
    """
    Extract the single-letter criterion code from a CRITERION IN FOCUS: line.
    Returns one of T, I, P, S, C, or N (Need), or "" if not found.
    """
    marker = "CRITERION IN FOCUS:"
    if marker not in text.upper():
        return ""
    idx  = text.upper().find(marker)
    line = text[idx + len(marker):].strip().split("\n")[0].upper()
    for ch in line:
        if ch in "TIPSCN":
            return ch
    return ""


# ── Criterion metadata ─────────────────────────────────────────
_CRITERION_NAMES = {
    "T": "Timely", "I": "Important", "P": "Profitable",
    "S": "Solvable", "C": "Contextual", "N": "Need Validation",
}

_CRITERION_SEARCH_GUIDANCE = {
    "T": "Search for market readiness and adoption trends.",
    "I": "Search for evidence of user pain points.",
    "P": "Search for monetization models and revenue opportunities.",
    "S": "Search for technical feasibility and available technology.",
    "C": "Search for regulations and contextual constraints.",
    "N": "Search for evidence that the need is real.",
}

_PSEA_SEARCH_GUIDANCE = {
    "P": "Search for competitors and problem-solution fit evidence.",
    "S": "Search for simpler alternatives.",
    "E": "Search for legal, privacy, and ethical requirements.",
    "A": "Search for market assumptions and adoption data.",
}


def force_close_instruction(criterion: str, turns: int) -> str:
    """
    Return an injected instruction block when a criterion has been probed
    too many times without being closed.  Empty string otherwise.
    """
    if turns < MAX_TURNS_PER_CRITERION:
        return ""
    name     = _CRITERION_NAMES.get(criterion, criterion)
    template = ui["force_close_template"]
    return template.format(turns=turns, name=name, criterion=criterion)


# ══════════════════════════════════════════════════════════════
# WEB SEARCH HELPERS
# ══════════════════════════════════════════════════════════════

def _serper_search(query: str) -> str:
    """
    Execute one Serper search and return compact formatted results.
    Called only from the fetch_* wrappers below — never from agent code.
    """
    num = _search["results_per_query"]
    timeout = _search["timeout_seconds"]
    web_cfg = ui["web_context"]

    if not _search_on:
        return web_cfg["search_off"]
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY":   _serper_key,
                "Content-Type": "application/json",
            },
            json={"q": query, "num": num},
            timeout=timeout,
        )
        data  = r.json()
        lines = []

        # Direct answer box (highest signal)
        ab      = data.get("answerBox", {})
        ab_text = ab.get("answer") or ab.get("snippet", "")
        if ab_text:
            lines.append(f"  [Direct answer] {ab_text.strip()}")

        # Organic snippets
        for item in data.get("organic", [])[:num]:
            title   = item.get("title", "").strip()
            snippet = item.get("snippet", "").strip()
            if title and snippet:
                lines.append(f"  • {title}: {snippet}")

        return "\n".join(lines) if lines else web_cfg["no_results"]
    except Exception as e:
        return web_cfg["error"].format(error=e)


def _fetch_web_context(queries: List[str], label: str) -> str:
    """
    Run a list of queries and return a formatted block ready to inject
    into a task description.  Returns empty string if search is off.
    """
    if not _search_on or not queries:
        return ""
    web_cfg  = ui["web_context"]
    date_str = datetime.now().strftime("%B %d, %Y")
    sep      = web_cfg["separator"]
    lines = [
        "",
        sep,
        web_cfg["header"].format(label=label, date=date_str),
        sep,
    ]
    for q in queries:
        lines.append(f'\nQuery: "{q}"')
        lines.append(_serper_search(q))
    lines += ["", sep, web_cfg["footer"].strip(), sep, ""]
    return "\n".join(lines)


def tipsc_search_context(problem: str) -> str:
    """Broad market context fetched once for the initial TIPSC triage."""
    yr    = datetime.now().year
    short = problem[:60].rstrip()
    return _fetch_web_context(
        [
            f"{short} market trends {yr}",
            f"{short} existing apps OR solutions",
            f"students college notifications communication pain points",
            f"{short} startup OR investment {yr}",
        ],
        label="TIPSC Triage",
    )


def criterion_search_context(criterion: str, problem: str) -> str:
    """
    Targeted context for the specific TIPSC criterion currently being probed.
    Queries are built from the actual problem text so they're always relevant.
    """
    yr    = datetime.now().year
    short = problem[:55].rstrip()
    queries_map = {
        "T": [f"{short} market readiness {yr}", f"{short} technology adoption rate"],
        "I": [f"{short} user pain points OR complaints", "students missing college updates notifications problem"],
        "P": [f"{short} business model monetization examples", f"EdTech student platform revenue model {yr}"],
        "S": [f"{short} technical feasibility build", f"{short} API OR integration tools available"],
        "C": [f"{short} data privacy regulations {yr}", "student app compliance requirements"],
        "N": [f"{short} unmet need evidence", f"{short} why existing solutions fail students"],
    }
    queries = queries_map.get(criterion, [f"{short} market opportunity {yr}"])
    return _fetch_web_context(queries, label=f"Criterion: {_CRITERION_NAMES.get(criterion, criterion)}")


def psea_search_context(problem: str, solution: str, issue: str = "") -> str:
    """
    Context for PSEA idea evaluation.  `issue` is one of P/S/E/A for targeted
    refinement searches; empty string triggers the broad initial-pass queries.
    """
    yr      = datetime.now().year
    short_p = problem[:50].rstrip()
    short_s = solution[:50].rstrip()

    config = {
        "P": (
            [f"{short_p} competitors OR existing solutions {yr}", f"{short_s} market differentiation"],
            "Problem-Solution Fit",
        ),
        "S": (
            [f"{short_s} minimum viable product examples", f"{short_p} simplest solution approach"],
            "Simplicity",
        ),
        "E": (
            [f"{short_s} privacy regulations data protection {yr}", f"{short_s} legal compliance requirements"],
            "Ethics & Compliance",
        ),
        "A": (
            [f"{short_p} market size statistics {yr}", f"{short_s} user adoption rate research"],
            "Assumptions",
        ),
    }
    queries, label = config.get(issue, (
        [f"{short_p} existing solutions competitors {yr}",
         f"{short_s} technical feasibility",
         f"{short_s} data privacy regulations"],
        "Solution Evaluation",
    ))
    return _fetch_web_context(queries, label=label)


# ══════════════════════════════════════════════════════════════
# AGENTS
# ══════════════════════════════════════════════════════════════

opportunity_agent = Agent(
    role=opp_p["agent"]["role"],
    goal=opp_p["agent"]["goal"],
    backstory=opp_p["agent"]["backstory"],
    verbose=False,
    tools=agent_tools,
    llm=llm,
)

idea_agent = Agent(
    role=idea_p["agent"]["role"],
    goal=idea_p["agent"]["goal"],
    backstory=idea_p["agent"]["backstory"],
    verbose=False,
    tools=agent_tools,
    llm=llm,
)


# ══════════════════════════════════════════════════════════════
# VALIDATION FLOW
# ══════════════════════════════════════════════════════════════

class ValidationFlow(Flow[ValidationState]):

    # ──────────────────────────────────────────────────────────
    # STEP 1 — Collect Problem
    # ──────────────────────────────────────────────────────────

    @start()
    def collect_problem(self):
        section(ui["section_titles"]["main"])
        print(ui["startup"]["intro"])
        hr()
        self.state.problem = ask(ui["prompts"]["problem_input"])
        return self.state.problem

    # ──────────────────────────────────────────────────────────
    # STEP 2 — TIPSC Triage (first pass)
    # ──────────────────────────────────────────────────────────

    @listen(collect_problem)
    def tipsc_triage(self, problem):
        section(ui["phases"]["opportunity_header"])
        print(ui["phases"]["opportunity_running"])

        description = opp_p["tasks"]["triage"].format(problem=problem)

        triage_task = Task(
            description=description,
            expected_output="Search findings, TIPSC triage, and opening question.",
            agent=opportunity_agent,
        )

        result = run_agent(triage_task, opportunity_agent)

        self.state.opp_history.append({"role": "agent", "content": result})
        self.state.opp_report  = result
        self.state.opp_status  = "IN_PROGRESS"

        return result

    # ──────────────────────────────────────────────────────────
    # STEP 3 — Opportunity Deep-Dive Loop
    #
    # Continues until the agent issues STATUS: APPROVED.
    # Code-level criterion turn tracking forces advancement so
    # the model cannot get stuck probing a single criterion.
    # ──────────────────────────────────────────────────────────

    @listen(tipsc_triage)
    def opportunity_loop(self, triage_result):
        report = triage_result

        while not opp_approved(report):

            agent_says(report)

            # Parse and track which criterion is active
            criterion = parse_criterion(report)
            if criterion:
                self.state.current_criterion = criterion
                self.state.criterion_turns[criterion] = (
                    self.state.criterion_turns.get(criterion, 0) + 1
                )
            turns_on_current = self.state.criterion_turns.get(
                self.state.current_criterion, 0
            )

            answer = ask(ui["prompts"]["response_input"])
            self.state.opp_history.append({"role": "user", "content": answer})

            last_q, last_a = last_exchange(self.state.opp_history)
            rep_warning    = repetition_warning(self.state.opp_last_q, last_q)
            force_close    = force_close_instruction(
                                 self.state.current_criterion, turns_on_current
                             )
            srch_guidance  = _CRITERION_SEARCH_GUIDANCE.get(
                                 self.state.current_criterion, ""
                             )
            history_text   = format_history(self.state.opp_history)

            description = opp_p["tasks"]["followup"].format(
                force_close    = force_close,
                rep_warning    = rep_warning,
                search_guidance = srch_guidance,
                last_q         = last_q,
                last_a         = last_a,
                problem        = self.state.problem,
                history        = history_text,
            )

            followup_task = Task(
                description=description,
                expected_output="Feedback, criterion tracking, then next question or approval.",
                agent=opportunity_agent,
            )

            report = run_agent(followup_task, opportunity_agent)
            self.state.opp_last_q = extract_question(report)
            self.state.opp_history.append({"role": "agent", "content": report})
            self.state.opp_report = report

        # Opportunity approved
        self.state.opp_status = "APPROVED"

        section(ui["section_titles"]["opp_valid"])
        print(report)

        hr("-")
        print(f"\n  {ui['transitions']['opportunity_approved']}\n")
        hr("-")

        self.state.solution = ask(ui["prompts"]["solution_input"])
        return self.state.solution

    # ──────────────────────────────────────────────────────────
    # STEP 4 — Initial PSEA Evaluation (first pass)
    # ──────────────────────────────────────────────────────────

    @listen(opportunity_loop)
    def evaluate_idea(self, solution):
        section(ui["phases"]["idea_header"])
        print(ui["phases"]["idea_running"])

        description = idea_p["tasks"]["initial_eval"].format(
            problem=self.state.problem,
            solution=solution,
        )

        eval_task = Task(
            description=description,
            expected_output="Search findings, PSEA evaluation with verdict.",
            agent=idea_agent,
        )

        result = run_agent(eval_task, idea_agent)

        self.state.idea_history.append({"role": "agent", "content": result})
        self.state.idea_report = result
        self.state.idea_status = "IN_PROGRESS"

        return result

    # ──────────────────────────────────────────────────────────
    # STEP 5 — Idea Refinement Loop
    #
    # Continues until the agent issues VERDICT: READY_FOR_DFV.
    # ──────────────────────────────────────────────────────────

    @listen(evaluate_idea)
    def idea_loop(self, eval_result):
        report = eval_result

        while not idea_ready(report):

            agent_says(report)

            answer = ask(ui["prompts"]["response_input"])
            self.state.idea_history.append({"role": "user", "content": answer})

            last_q, last_a = last_exchange(self.state.idea_history)
            rep_warning    = repetition_warning(self.state.idea_last_q, last_q)
            history_text   = format_history(self.state.idea_history)

            # Parse which PSEA criterion is active for targeted search guidance
            active_issue = ""
            if "ISSUE IN FOCUS:" in report.upper():
                idx  = report.upper().find("ISSUE IN FOCUS:")
                line = report[idx + len("ISSUE IN FOCUS:"):].strip().split("\n")[0].upper()
                for ch in line:
                    if ch in "PSEA":
                        active_issue = ch
                        break
            psea_search = _PSEA_SEARCH_GUIDANCE.get(active_issue, "")

            description = idea_p["tasks"]["refinement"].format(
                rep_warning    = rep_warning,
                search_guidance = psea_search,
                last_q         = last_q,
                last_a         = last_a,
                problem        = self.state.problem,
                solution       = self.state.solution,
                history        = history_text,
            )

            refinement_task = Task(
                description=description,
                expected_output="Search findings, feedback, then next question or DFV clearance.",
                agent=idea_agent,
            )

            report = run_agent(refinement_task, idea_agent)
            self.state.idea_last_q = extract_question(report)
            self.state.idea_history.append({"role": "agent", "content": report})
            self.state.idea_report = report

        self.state.idea_status = "READY_FOR_DFV"
        return report

    # ──────────────────────────────────────────────────────────
    # STEP 6 — Final Report
    # ──────────────────────────────────────────────────────────

    @listen(idea_loop)
    def final_report(self, idea_result):
        labels = ui["report_labels"]

        section(ui["section_titles"]["final"])

        hr("-")
        print(f"  {labels['problem']}")
        hr("-")
        print(f"  {self.state.problem}")
        print()

        hr("-")
        print(f"  {labels['opportunity']}")
        hr("-")
        print(self.state.opp_report)
        print()

        hr("-")
        print(f"  {labels['solution']}")
        hr("-")
        print(f"  {self.state.solution}")
        print()

        hr("-")
        print(f"  {labels['idea']}")
        hr("-")
        print(idea_result)
        print()

        section(ui["section_titles"]["dfv_ready"])
        print(f"  {ui['transitions']['final_status']}\n")
        hr()

        self.state.idea_status = "COMPLETE"
        return idea_result


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        flow = ValidationFlow()
        flow.kickoff()
    except KeyboardInterrupt:
        print("\n\n  Session interrupted. Exiting.\n")
        sys.exit(0)
