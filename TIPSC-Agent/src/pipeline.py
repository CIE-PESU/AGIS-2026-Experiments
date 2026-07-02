import os,re
import json
from crewai import Agent, Crew, LLM, Process, Task
from crewai_tools import TavilySearchTool
from models import PreEvalOutput, TIPSCOutput, FollowUpOutput, EthicsOutput, ValidationOutput, RegulatoryOutput



os.environ["TAVILY_API_KEY"] = "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"   # ← paste your key
search_tool = TavilySearchTool()


def clean_json(text: str) -> str:
    text = text.strip()
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()
    # Extract first complete JSON object using depth tracking
    depth = 0
    start = None
    in_string = False
    escape_next = False
    out = []
    CTRL_ESCAPES = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}
    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            if start is not None:
                out.append(ch)
            continue
        if ch == "\\" and in_string:
            escape_next = True
            if start is not None:
                out.append(ch)
            continue
        if ch == '"':
            in_string = not in_string
            if start is not None:
                out.append(ch)
            continue
        if in_string:
            if start is not None:
                if ch in CTRL_ESCAPES:
                    out.append(CTRL_ESCAPES[ch])
                elif ord(ch) < 0x20:
                    out.append(f"\\u{ord(ch):04x}")
                else:
                    out.append(ch)
            continue
        if ch == "{":
            if depth == 0:
                start = i
                out = ["{"]
            else:
                out.append(ch)
            depth += 1
        elif ch == "}":
            depth -= 1
            if start is not None:
                out.append(ch)
            if depth == 0 and start is not None:
                return "".join(out)
        elif start is not None:
            out.append(ch)
 
    raise ValueError(
        f"clean_json: no complete JSON object found.\nFirst 200 chars: {text[:200]!r}"
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

    non_system = [m for m in messages if m.get("role") != "system"]
    enforced = [{"role": "system", "content": JSON_SYSTEM_PREFIX}] + non_system 
    return llm.call(enforced).strip()
 

def run_preeval(llm: LLM, skill_text: str, preeval_input: dict,) -> PreEvalOutput:

    founder_context = f"""
    Problem Statement:
    {preeval_input["problem_statement"]}

    Customer Segment:
    {preeval_input["customer_segment"]}

    Consequence:
    {preeval_input["consequence"]}

    Assumptions:
    {preeval_input["assumptions"]}

    Proposed Solution:
    {preeval_input["proposed_solution"]}

    Target Geography:
    {preeval_input["target_geography"]}

    Industry Sector:
    {preeval_input["industry_sector"]}
    """.strip()
    messages = [
        {"role": "system", "content": skill_text},
        {
            "role": "user",
            "content": f"""
                The founder has completed the pre-evaluation questionnaire.

                {founder_context}

                Convert the founder's responses into the following JSON schema.
                
                {{
                "problem_statement": "one sentence describing the core problem",
                "customer_segment": "who experiences the problem",
                "consequence": "what happens if unsolved",
                "assumptions": ["assumption 1", "assumption 2"],
                "proposed_solution": "what the team plans to build",
                "target_geography": "primary country or region being targeted",
                "industry_sector": "the industry or sector the solution operates in"
                }}

                Normalize grammar and wording where appropriate without changing the founder's intended meaning.

                Do not invent, infer, or assume any information that is not explicitly provided.                
                Output ONLY valid JSON.
            """
        }
    ]

    raw = clean_json(call_llm_for_json(llm,messages))

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
            '  "proposed_solution": "...",\n'
            '  "target_geography": "...",\n'
            '  "industry_sector": "..."\n'
            "}"
        )
        retry_messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": retry_prompt},
        ]
        raw2 = clean_json(call_llm_for_json(llm, retry_messages))
        return PreEvalOutput.model_validate_json(raw2)


# ── Phase 2: Validation ────────────────────────────────────────────────────────


def normalize_validation_dict(data: dict, preeval: PreEvalOutput) -> dict:
    """Coerce common malformed shapes from small local models into the
    flat ValidationOutput schema before pydantic validation is attempted.
    This handles the model nesting fields under a single key (e.g.
    {'competitor_landscape': {...everything...}}) instead of returning
    the flat object that was asked for.
    """
    if not isinstance(data, dict):
        return data
 
    # Case: model wrapped the whole payload under one top-level key
    # e.g. {"competitor_landscape": {"geography": ..., "checked_assumptions": [...]}}
    known_keys = {
        "target_geography", "industry_sector", "checked_assumptions",
        "competitor_landscape", "market_notes", "validation_summary",
    }
    if not (known_keys & data.keys()) and len(data) == 1:
        inner = next(iter(data.values()))
        if isinstance(inner, dict):
            data = inner
 
    # competitor_landscape returned as dict instead of string -> stringify it
    cl = data.get("competitor_landscape")
    if isinstance(cl, dict):
        parts = [f"{k}: {v}" for k, v in cl.items()]
        data["competitor_landscape"] = "; ".join(parts)
    elif isinstance(cl, list):
        data["competitor_landscape"] = "; ".join(str(x) for x in cl)
 
    # market_notes returned as dict/list -> stringify
    mn = data.get("market_notes")
    if isinstance(mn, (dict, list)):
        data["market_notes"] = json.dumps(mn, default=str)


    # Normalize verdict strings in checked_assumptions.
    # Small models like Mistral 7B decorate verdicts with extra text, e.g.
    # "CONFIRMED WITH SOME UNCERTAINTY" instead of the bare enum value.
    # We prefix-match to recover the canonical value before Pydantic sees it.
    _VERDICT_PREFIXES = ("CONFIRMED", "UNCONFIRMED", "CONTRADICTED")
    assumptions = data.get("checked_assumptions")
    if isinstance(assumptions, list):
        for item in assumptions:
            if not isinstance(item, dict):
                continue
            raw_verdict = str(item.get("verdict", "")).strip().upper()
            for canonical in _VERDICT_PREFIXES:
                if raw_verdict.startswith(canonical):
                    if raw_verdict != canonical:
                        print(f"  [Auto-correct] verdict: {item['verdict']!r} -> {canonical!r}")
                    item["verdict"] = canonical
                    break
            else:
                # No prefix matched — fall back to UNCONFIRMED so Pydantic doesn't crash
                print(f"  [Auto-correct] unrecognised verdict {item.get('verdict')!r} -> 'UNCONFIRMED'")
                item["verdict"] = "UNCONFIRMED"

    # Normalize validation_summary the same way (e.g. "MIXED - see notes")
    _SUMMARY_PREFIXES = ("STRONG", "MIXED", "WEAK")
    vs = str(data.get("validation_summary", "")).strip().upper()
    for canonical in _SUMMARY_PREFIXES:
        if vs.startswith(canonical):
            if vs != canonical:
                print(f"  [Auto-correct] validation_summary: {data['validation_summary']!r} -> {canonical!r}")
            data["validation_summary"] = canonical
            break

    # fall back to preeval values for required fields the model dropped
    data.setdefault("target_geography", preeval.target_geography)
    data.setdefault("industry_sector", preeval.industry_sector)
    data.setdefault("checked_assumptions", [])
    data.setdefault("competitor_landscape", "No competitor data found.")
    data.setdefault("market_notes", "No additional market notes.")
    data.setdefault("validation_summary", "WEAK")
 
    return data
 

def run_validation(
    llm: LLM,
    preeval: PreEvalOutput,
    agents_cfg: dict,
    task_cfg: dict,
) -> ValidationOutput:
    research_agent = Agent(
        role=agents_cfg["validation_agent"]["role"],
        goal=agents_cfg["validation_agent"]["goal"],
        backstory=agents_cfg["validation_agent"]["backstory"],
        llm=llm,
        tools=[search_tool],
        max_iter=8,
        max_execution_time=int(os.environ.get("VALIDATION_TIMEOUT_SECS", 600)),
    )
 
    research_task = Task(
        description=task_cfg["validation_task"]["description"].format(
            preeval_json=preeval.model_dump_json(indent=2),
        ),
        expected_output=(
            "A plain-text research summary covering, for each assumption: "
            "what was searched, what was found, and a CONFIRMED/UNCONFIRMED/"
            "CONTRADICTED call. Also include a competitor landscape paragraph "
            "and any market notes. This does NOT need to be JSON yet."
        ),
        agent=research_agent,
    )
 
    crew = Crew(
        agents=[research_agent],
        tasks=[research_task],
        process=Process.sequential,
        verbose=False,
    )
 
    try:
        result = crew.kickoff()
        research_notes = result.raw
    except TimeoutError:
        print("  Validation research timed out before completing all searches. "
              "Falling back to assumptions-only validation (no search evidence).")
        research_notes = (
            "Research did not complete in time. No search evidence was gathered. "
            "Treat every assumption below as UNCONFIRMED with evidence "
            "'No evidence found — research timed out.'\n\n"
            f"Assumptions to cover:\n"
            + "\n".join(f"- {a}" for a in preeval.assumptions)
        )
 
    # Step 2: format-only pass (no tools, no ReAct loop). A separate,
    # single-shot call whose only job is to convert the research notes
    # above into the exact flat schema.
    schema_hint = json.dumps(ValidationOutput.model_json_schema(), indent=2)
    format_prompt = (
        "Convert the research notes below into ONE flat JSON object that "
        "matches this exact structure. Do NOT nest fields under any extra "
        "top-level key — target_geography, industry_sector, "
        "checked_assumptions, competitor_landscape, market_notes, and "
        "validation_summary must all be top-level keys.\n\n"
        f"Target schema (for reference, not literal output):\n{schema_hint}\n\n"
        "Required shape:\n"
        "{\n"
        '  "target_geography": "...",\n'
        '  "industry_sector": "...",\n'
        '  "checked_assumptions": [\n'
        '    {"assumption": "...", "verdict": "CONFIRMED|UNCONFIRMED|CONTRADICTED", "evidence": "..."}\n'
        "  ],\n"
        '  "competitor_landscape": "one paragraph string, not an object",\n'
        '  "market_notes": "string",\n'
        '  "validation_summary": "STRONG|MIXED|WEAK"\n'
        "}\n\n"
        "If a field is missing from the notes, use a sensible default "
        "('No evidence found.' for evidence, 'UNCONFIRMED' for verdict). "
        "competitor_landscape and market_notes MUST be plain strings, "
        "never objects or arrays.\n\n"
        f"Research notes:\n{research_notes}"
    )
 
    def _attempt_format(prompt_text: str) -> ValidationOutput:
        raw = call_llm_for_json(llm, [{"role": "user", "content": prompt_text}])
        cleaned = clean_json(raw)
        data = normalize_validation_dict(json.loads(cleaned), preeval)
        return ValidationOutput.model_validate(data)
 
    try:
        return _attempt_format(format_prompt)
    except Exception as e:
        print(f"  Validation formatting failed ({e}). Retrying once with a "
              "stricter, schema-only prompt...")
        stricter_prompt = (
            "Your previous output did not match the required flat JSON "
            "schema. Output ONLY the JSON object below, filled in, with "
            "no nesting beyond what is shown:\n\n"
            "{\n"
            f'  "target_geography": "{preeval.target_geography}",\n'
            f'  "industry_sector": "{preeval.industry_sector}",\n'
            '  "checked_assumptions": [{"assumption": "...", "verdict": "UNCONFIRMED", "evidence": "No evidence found."}],\n'
            '  "competitor_landscape": "...",\n'
            '  "market_notes": "...",\n'
            '  "validation_summary": "MIXED"\n'
            "}\n\n"
            f"Research notes:\n{research_notes}"
        )
        try:
            return _attempt_format(stricter_prompt)
        except Exception as e2:
            print(f"ERROR: Recovery retry also failed: {e2}")
            print("Raw research notes (original):")
            print(research_notes)
            raise


# ── Phase 3: Regulatory mapping ───────────────────────────────────────────────

def normalize_regulatory_dict(data: dict, preeval: PreEvalOutput) -> dict:
    if not isinstance(data, dict):
        return data
    known_keys = {
        "target_geography", "industry_sector", "applicable_regulations",
        "regulatory_summary", "requires_specialist_review", "key_compliance_risks",
    }
    if not (known_keys & data.keys()) and len(data) == 1:
        inner = next(iter(data.values()))
        if isinstance(inner, dict):
            data = inner
    rs = data.get("regulatory_summary")
    if isinstance(rs, list):
        data["regulatory_summary"] = " ".join(str(x) for x in rs)
    elif rs is None:
        data["regulatory_summary"] = "No regulatory summary available."
    kcr = data.get("key_compliance_risks")
    if isinstance(kcr, str):
        data["key_compliance_risks"] = [kcr] if kcr else []
    elif kcr is None:
        data["key_compliance_risks"] = []
    ar = data.get("applicable_regulations")
    if not isinstance(ar, list):
        data["applicable_regulations"] = []
    rsr = data.get("requires_specialist_review")
    if isinstance(rsr, str):
        data["requires_specialist_review"] = rsr.strip().lower() == "true"
    data.setdefault("target_geography", preeval.target_geography)
    data.setdefault("industry_sector", preeval.industry_sector)
    data.setdefault("requires_specialist_review", False)
    return data


def run_regulatory(
    llm: LLM,
    preeval: PreEvalOutput,
    agents_cfg: dict,
    task_cfg: dict,
) -> "RegulatoryOutput":
 
    agent = Agent(
        role=agents_cfg["regulatory_agent"]["role"],
        goal=agents_cfg["regulatory_agent"]["goal"],
        backstory=agents_cfg["regulatory_agent"]["backstory"],
        llm=llm,
        tools=[search_tool],
        max_iter=6,
        max_execution_time=int(os.environ.get("REGULATORY_TIMEOUT_SECS", 300)),
    )
 
    task = Task(
        description=task_cfg["regulatory_task"]["description"].format(
            preeval_json=preeval.model_dump_json(indent=2),
        ),
        expected_output=task_cfg["regulatory_task"]["expected_output"],
        agent=agent,
    )
 
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
 
    try:
        result = crew.kickoff()
        research_notes = result.raw
    except TimeoutError:
        print("  Regulatory research timed out. Returning minimal regulatory output.")
        research_notes = None
 
    if research_notes is None:
        return RegulatoryOutput(
            target_geography=preeval.target_geography,
            industry_sector=preeval.industry_sector,
            applicable_regulations=[],
            regulatory_summary="Regulatory research did not complete in time. Manual review recommended.",
            requires_specialist_review=True,
            key_compliance_risks=["Research timed out — specialist review required."],
        )
 
    schema_hint = json.dumps(RegulatoryOutput.model_json_schema(), indent=2)
    format_prompt = (
        "Convert the regulatory research notes below into ONE flat JSON object "
        "matching this exact structure. Do NOT nest fields under any extra top-level key.\n\n"
        f"Target schema (for reference):\n{schema_hint}\n\n"
        "Required shape:\n"
        "{\n"
        '  "target_geography": "...",\n'
        '  "industry_sector": "...",\n'
        '  "applicable_regulations": [\n'
        '    {"name": "...", "jurisdiction": "...", "compliance_burden": "HIGH|MEDIUM|LOW", "brief_requirement": "..."}\n'
        "  ],\n"
        '  "regulatory_summary": "one paragraph string",\n'
        '  "requires_specialist_review": true or false,\n'
        '  "key_compliance_risks": ["risk 1", "risk 2"]\n'
        "}\n\n"
        "If no regulations apply, use an empty list for applicable_regulations.\n"
        "regulatory_summary and key_compliance_risks MUST be a plain string and plain list respectively.\n\n"
        f"Research notes:\n{research_notes}"
    )
 
    def _attempt_format(prompt_text: str) -> "RegulatoryOutput":
        raw = call_llm_for_json(llm, [{"role": "user", "content": prompt_text}])
        cleaned = clean_json(raw)
        data = normalize_regulatory_dict(json.loads(cleaned), preeval)
        return RegulatoryOutput.model_validate(data)
 
    try:
        return _attempt_format(format_prompt)
    except Exception as e:
        print(f"  Regulatory formatting failed ({e}). Retrying with stricter prompt...")
        stricter_prompt = (
            "Your previous output did not match the required flat JSON schema. "
            "Output ONLY the JSON object below, filled in:\n\n"
            "{\n"
            f'  "target_geography": "{preeval.target_geography}",\n'
            f'  "industry_sector": "{preeval.industry_sector}",\n'
            '  "applicable_regulations": [],\n'
            '  "regulatory_summary": "Regulatory research incomplete. Manual review recommended.",\n'
            '  "requires_specialist_review": true,\n'
            '  "key_compliance_risks": ["Manual specialist review required."]\n'
            "}\n\n"
            f"Research notes:\n{research_notes}"
        )
        try:
            return _attempt_format(stricter_prompt)
        except Exception as e2:
            print(f"ERROR: Regulatory recovery retry also failed: {e2}")
            print("Falling back to safe default RegulatoryOutput.")
            return RegulatoryOutput(
                target_geography=preeval.target_geography,
                industry_sector=preeval.industry_sector,
                applicable_regulations=[],
                regulatory_summary="Regulatory formatting failed. Manual review recommended.",
                requires_specialist_review=True,
                key_compliance_risks=["Formatting error — specialist review required."],
            )
 

 # ── Phase 4: Ethics pre-screen ────────────────────────────────────────────────
 
 
def run_ethics(
    llm: LLM,
    preeval: PreEvalOutput,
    agents_cfg: dict,
    task_cfg: dict,
    ethics_rubric: str,
    validation_context: str = "",
    regulatory_context: str = "",
) -> EthicsOutput:
    agent = Agent(
        role=agents_cfg["ethics_agent"]["role"],
        goal=agents_cfg["ethics_agent"]["goal"],
        backstory=agents_cfg["ethics_agent"]["backstory"],
        llm=llm,
    )

    task = Task(
        description=task_cfg["ethics_task"]["description"].format(
            ethics_rubric=ethics_rubric,
            preeval_json=preeval.model_dump_json(indent=2),
            validation_context=validation_context if validation_context else "Not yet available.",
            regulatory_context=regulatory_context if regulatory_context else "Not yet available.",
        ),
        expected_output=task_cfg["ethics_task"]["expected_output"],
        agent=agent,
    )
 
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()

    try:
        return parse_pydantic_result(result, EthicsOutput)
    except Exception as e:
        print(f"ERROR: Could not parse Ethics output: {e}")
        print("Raw output:")
        print(result.raw)
        raise
 

def run_tipsc(
    llm: LLM,
    preeval: PreEvalOutput,
    agents_cfg: dict,
    task_cfg: dict,
    rubric: str,
    validation_context: str = "",
    compliance_context: str = "",
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
            validation_context=validation_context if validation_context else "Not yet available.",
            compliance_context=compliance_context if compliance_context else "No compliance concerns flagged.",
            followup_context=followup_context if followup_context else "None provided.",
        ),
        expected_output=task_cfg["tipsc_task"]["expected_output"],
        agent=agent,
        )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()

    try:
        return parse_pydantic_result(result, TIPSCOutput)
    except Exception as e:
        print(f"ERROR: Could not parse TIPSC output: {e}")
        print("Raw output:")
        print(result.raw)
        raise


def run_followup(
    llm: LLM,
    tipsc_output: TIPSCOutput,
    agents_cfg: dict,
    task_cfg: dict,
    followup_context: str = "",  # FIX: pass accumulated prior Q&A
    compliance_context: str = "",
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
            compliance_context=compliance_context if compliance_context else "No compliance concerns flagged.",
            followup_context=followup_context if followup_context else "None yet.",
        ),
        expected_output=task_cfg["followup_task"]["expected_output"],
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()

    try:
        return parse_pydantic_result(result, FollowUpOutput)
    except Exception as e:
        print(f"ERROR: Could not parse Follow-up output: {e}")
        print("Raw output:")
        print(result.raw)
        raise


def build_compliance_context(ethics: EthicsOutput, regulatory: "RegulatoryOutput") -> str:
    """
    Build a plain-text compliance summary to pass to TIPSC and follow-up agents.
    Returns an empty string if no compliance flag is set — agents treat that as
    'no regulatory concern, score S on technical capability alone'.
    """
    if not ethics.compliance_flag:
        return ""
 
    lines = [
        "COMPLIANCE NOTICE: This idea operates in a regulated space.",
        f"Specialist review required: {regulatory.requires_specialist_review}",
        f"Ethics legal risk verdict: {ethics.legal_risk} — {ethics.legal_reason}",
        "",
    ]
 
    if regulatory.applicable_regulations:
        lines.append("Applicable regulations:")
        for r in regulatory.applicable_regulations:
            lines.append(
                f"  - {r.name} ({r.jurisdiction}) "
                f"[{r.compliance_burden} burden]: {r.brief_requirement}"
            )
        lines.append("")
 
    if regulatory.key_compliance_risks:
        lines.append("Key compliance risks:")
        for risk in regulatory.key_compliance_risks:
            lines.append(f"  - {risk}")
        lines.append("")
 
    lines.append(f"Regulatory summary: {regulatory.regulatory_summary}")
 
    return "\n".join(lines)


def parse_pydantic_result(result, model):
    if result.pydantic and isinstance(result.pydantic, model):
        return result.pydantic
 
    raw = clean_json(result.raw)
    return model.model_validate_json(raw)