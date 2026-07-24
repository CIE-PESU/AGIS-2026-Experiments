
from dataclasses import dataclass
import os
import json
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from pathlib import Path
from pydantic import BaseModel, Field
from typing import ClassVar
from crewai.skills import discover_skills, activate_skill
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
import re

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

import litellm
litellm.drop_params = True

# LM Studio's OpenAI-compatible server only accepts tool_choice as a plain
# string ("none" | "auto" | "required"). Depending on the internal CrewAI
# code path (native tool-calling, forced structured output, etc.), CrewAI/
# LiteLLM sometimes builds the modern object-style tool_choice instead, e.g.
# {"type": "function", "function": {"name": "..."}}. LM Studio rejects that
# with a 400. Rather than chase every internal call site that might build
# this object, we sanitize it at the litellm.completion/acompletion boundary
# -- the last point before the request actually goes out over the network.
_original_litellm_completion = litellm.completion
_original_litellm_acompletion = litellm.acompletion


def _sanitize_tool_choice(kwargs):
    tool_choice = kwargs.get("tool_choice")
    if isinstance(tool_choice, dict):
        # Force -> "required" (still compels a tool call, just via the
        # string form LM Studio understands). Anything else -> "auto".
        tc_type = tool_choice.get("type")
        kwargs["tool_choice"] = "required" if tc_type in ("function", "tool") else "auto"
    return kwargs


def _patched_litellm_completion(*args, **kwargs):
    kwargs = _sanitize_tool_choice(kwargs)
    
    # ── INSTRUMENTATION: Log prompt details before sending ──
    messages = kwargs.get("messages", [])
    total_chars = sum(len(m.get("content") or "") for m in messages)
    system_chars = sum(len(m.get("content") or "") for m in messages if m.get("role") == "system")
    user_chars = sum(len(m.get("content") or "") for m in messages if m.get("role") == "user")
    assistant_chars = sum(len(m.get("content") or "") for m in messages if m.get("role") == "assistant")
    
    # Simple token estimation (~4 characters per token)
    est_prompt_tokens = int(total_chars / 4)
    
    # Attempt to read target model context window from LM Studio API
    context_window = 32768  # Default Qwen/Llama context window fallback
    try:
        import urllib.request
        base_url = kwargs.get("base_url") or os.environ.get("LM_STUDIO_URL")
        if base_url:
            model_info_url = base_url.rstrip("/") + "/models"
            with urllib.request.urlopen(model_info_url, timeout=2.0) as req:
                info = json.loads(req.read().decode())
                # If LM Studio exposes metadata or model list
                if "data" in info and len(info["data"]) > 0:
                    # Fallback to standard context length for detected model names
                    model_id = info["data"][0].get("id", "").lower()
                    if "qwen" in model_id:
                        context_window = 32768
                    elif "phi" in model_id:
                        context_window = 16384
                    elif "llama" in model_id:
                        context_window = 131072
    except Exception:
        pass
        
    context_usage_pct = (est_prompt_tokens / context_window) * 100
    
    # Attempt to extract agent role or model configuration name to represent the active "user" in logs
    agent_name = "Unknown Agent"
    for m in messages:
        # Check system prompts for agent identity hints
        content = m.get("content") or ""
        if "You are the " in content:
            # e.g., "You are the Desirability Evaluation Agent"
            start_idx = content.find("You are the ") + 12
            end_idx = content.find(".", start_idx)
            if end_idx != -1:
                agent_name = content[start_idx:end_idx].strip()
                break
        elif "role=" in content:
            # fallback parameter check
            agent_name = content.split("role=")[1].split(",")[0].strip("'\"")
            break

    print("\n" + "="*50)
    print("      LITELLM COMPLETION INSTRUMENTATION")
    print("="*50)
    print(f"Active Agent (User Name):            {agent_name}")
    print(f"Total System Prompt Size (chars):   {system_chars}")
    print(f"Total User/Task Prompt Size (chars): {user_chars}")
    print(f"Total Assistant History Size (chars):{assistant_chars}")
    print(f"Total Combined Payload Size (chars): {total_chars}")
    print(f"Estimated Prompt Token Count:        {est_prompt_tokens}")
    print(f"Target Model Context Window Limit:   {context_window}")
    print(f"Estimated Context Window Usage:      {context_usage_pct:.2f}%")
    print("="*50 + "\n")

    max_retries = 3
    for attempt in range(max_retries):
        res = _original_litellm_completion(*args, **kwargs)
        if res and hasattr(res, "choices") and len(res.choices) > 0:
            msg = res.choices[0].message
            content = getattr(msg, "content", None)
            tool_calls = getattr(msg, "tool_calls", None)
            if content or tool_calls:
                print(f"[litellm_patch] SUCCESS: Attempt {attempt + 1} returned valid content.")
                return res
            if attempt < max_retries - 1:
                print(f"[litellm_patch] WARNING: Empty response (attempt {attempt + 1}/{max_retries}). Retrying...")
                continue
        return res
    return res


async def _patched_litellm_acompletion(*args, **kwargs):
    kwargs = _sanitize_tool_choice(kwargs)
    
    messages = kwargs.get("messages", [])
    total_chars = sum(len(m.get("content") or "") for m in messages)
    system_chars = sum(len(m.get("content") or "") for m in messages if m.get("role") == "system")
    user_chars = sum(len(m.get("content") or "") for m in messages if m.get("role") == "user")
    assistant_chars = sum(len(m.get("content") or "") for m in messages if m.get("role") == "assistant")
    est_prompt_tokens = int(total_chars / 4)
    context_window = 32768
    context_usage_pct = (est_prompt_tokens / context_window) * 100
    
    # Attempt to extract agent role or model configuration name to represent the active "user" in logs
    agent_name = "Unknown Agent"
    for m in messages:
        content = m.get("content") or ""
        if "You are the " in content:
            start_idx = content.find("You are the ") + 12
            end_idx = content.find(".", start_idx)
            if end_idx != -1:
                agent_name = content[start_idx:end_idx].strip()
                break
        elif "role=" in content:
            agent_name = content.split("role=")[1].split(",")[0].strip("'\"")
            break

    print("\n" + "="*50)
    print("      LITELLM ASYNC COMPLETION INSTRUMENTATION")
    print("="*50)
    print(f"Active Agent (User Name):            {agent_name}")
    print(f"Total System Prompt (chars):         {system_chars}")
    print(f"Total User/Task Prompt (chars):       {user_chars}")
    print(f"Total Assistant History (chars):      {assistant_chars}")
    print(f"Total Combined Payload (chars):       {total_chars}")
    print(f"Estimated Prompt Token Count:        {est_prompt_tokens}")
    print(f"Estimated Context Window Usage:      {context_usage_pct:.2f}%")
    print("="*50 + "\n")

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
                print(f"[litellm_patch] WARNING: Empty async response (attempt {attempt + 1}/{max_retries}). Retrying...")
                continue
        return res
    return res


litellm.completion = _patched_litellm_completion
litellm.acompletion = _patched_litellm_acompletion

now = datetime.now()
TodayDate = now.strftime("%d - %B - %Y")

# Patch cache breakpoint for providers like Groq/Ollama if needed
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

# Monkey patch LLM.supports_function_calling to return False for Groq models
original_supports_function_calling = LLM.supports_function_calling

def patched_supports_function_calling(self) -> bool:
    model_name = self.model or ""
    provider = getattr(self, "provider", None) or self._get_custom_llm_provider()
    if "groq" in model_name.lower() or provider == "groq":
        return False
    if "qwen" in model_name.lower():
        return False
    return original_supports_function_calling(self)

LLM.supports_function_calling = patched_supports_function_calling


SERPER_API_KEY = os.getenv("SERPER_API_KEY")
os.environ["SERPER_API_KEY"] = SERPER_API_KEY or ""

# Initialize tools required for Phase 1 Desirability market analysis
search_tool = SerperDevTool(api_key=SERPER_API_KEY)


class TruncatedScrapeWebsiteTool(ScrapeWebsiteTool):
    """ScrapeWebsiteTool returns a full page's raw text with no length cap.
    A single scraped page can easily run 20k+ characters, which blows past
    the local qwen model's context window in LM Studio (especially once
    combined with the system prompt, task description, and prior tool
    results in the ReAct-style conversation). This caps it to a safe size."""

    MAX_CHARS: ClassVar[int] = 6000  # ~1500-2000 tokens; leaves headroom for the rest of the context

    def _run(self, **kwargs):
        result = super()._run(**kwargs)
        if isinstance(result, str) and len(result) > self.MAX_CHARS:
            return result[: self.MAX_CHARS] + "\n\n[...truncated: page content exceeded length limit...]"
        return result


scrape_tool = TruncatedScrapeWebsiteTool()



llm = LLM(
    model=os.environ["OPENAI_MODEL_NAME"],
    base_url=os.environ["LM_STUDIO_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
    temperature=0.1,
    timeout=108000,
)

# Discover and activate local business framework guidelines from markdown packages
skills = discover_skills(Path(__file__).parent / "skills")
activated = [activate_skill(s) for s in skills]

# Define the Pydantic models for JSON output (Updated with Go/No-Go architecture)
class RefinedIdea(BaseModel):
    customer_segment: str = Field(description="A precise description of the target customer segment for this proposal, identifying who specifically experiences the problem (e.g. demographics, role, location, or behavioral traits), based strictly on the information given.")
    qualified_problem: str = Field(description="The specific, qualified problem or pain point this proposal addresses, stated clearly enough to show why it is a real and recurring issue for the identified customer segment.")
    consequence: str = Field(description="The direct negative consequence the customer segment faces if this problem remains unsolved, expressed in concrete terms (e.g. financial, time, opportunity, or experiential cost).")
    proposed_solution: str = Field(description="A concise description of the product, service, or solution being proposed to address the qualified problem, capturing its core mechanism and how it delivers value to the customer.")

class Hypotheses(BaseModel):
    desirability_statement: str = Field(description="A 'We believe [target customer] will [specific action/behavior]...' hypothesis statement that tests whether the target customer cares enough about the identified problem to adopt the proposed solution.")
    feasibility_statement: str = Field(description="A 'We believe [team/resource] can [build/deliver action] within [timeframe] using [tools/methods]...' hypothesis statement that tests whether the proposed solution can realistically be built or delivered with the resources and constraints described.")
    viability_statement: str = Field(description="A 'We believe we can sustain/grow this by [revenue model or business approach]...' hypothesis statement that tests whether the proposed business model can generate enough value to remain financially sustainable.")

class TipsValidatedMetrics(BaseModel):
    timely_factor: str = Field(description="The urgency/timeliness factor explaining why this problem matters to solve right now, based on any relevant trends, changes, deadlines, or shifting conditions mentioned in the proposal.")
    importance_metric: str = Field(description="The importance/severity metric explaining how significant the consequence is for the target customer, and why it matters enough to justify a solution.")
    profitability_pivot: str = Field(description="The core revenue or business model approach for this proposal, identifying who pays, how, and why that payer is willing to do so.")
    solvability_constraint: str = Field(description="The technical or operational feasibility constraint showing the proposed solution can realistically be implemented given the resources, tools, or infrastructure described in the proposal.")

class DecisionGate(BaseModel):
    status: str = Field(description="The definitive operational verdict for this proposal. Must be strictly either 'GO' (all three DFV dimensions - Desirability, Feasibility, Viability - pass without a fatal flaw) or 'NO-GO' (at least one dimension reveals a fatal flaw requiring a major structural pivot).")
    justification: str = Field(description="A concise, evidence-based explanation of the single most critical factor (positive or negative) across the Desirability, Feasibility, and Viability reports that determined the GO or NO-GO status.")

class DFAOutput(BaseModel):
    refined_idea: RefinedIdea
    hypotheses: Hypotheses 
    tips_validated_metrics: TipsValidatedMetrics
    final_decision: DecisionGate

def create_dfv_crew():
    desirability_agent = Agent(
        role="Desirability Evaluation Agent",
        goal=f"Determine whether the proposed solution addresses a genuine user need and whether sufficient market demand exists. Today's Date {TodayDate}",
        backstory=(
            """You are an expert market research analyst and user experience strategist. You MUST use the Search tool and ScrapeWebsite tool for EVERY task.
        Do NOT answer from memory or prior knowledge.
        Your first action must always be a tool call.
        If you have not searched the web, your answer is incomplete.
            """
        ),
        llm=llm,
        tools=[search_tool, scrape_tool],
        verbose=False,
        skills=[activated[0]],
        max_iter=7
    )

    desirability_task = Task(
        description="{desirability}",
        expected_output=(
            "A formal text-formatted 'Desirability Analysis Report' containing:\n"
            "1. User Demand Analysis (validating target user pain points and problem severity).\n"
            "2. Market Demand Assessment (current industry search interest and growth indicators).\n"
            "3. Competitor Analysis (gaps, weaknesses, or friction in existing products/alternatives).\n"
            "4. Opportunity Identification (clear statement on why this solution is or is not desired by the market).\n"
            "keep the output under 600 words"
        ),
        agent=desirability_agent,
        async_execution=False
    )

    feasibility_agent = Agent(
        role="Feasibility Evaluation Agent",
        goal=f"Evaluate the feasibility of a startup idea strictly from the Feasibility dimension of the DFV framework. Today's Date {TodayDate}",
        backstory=(
            """You are an expert technical architect, systems analyst, and execution strategist. You MUST use the Search tool and ScrapeWebsite tool for EVERY task.
        Do NOT answer from memory or prior knowledge.
        Your first action must always be a tool call.
        If you have not searched the web, your answer is incomplete. """
        ),
        llm=llm,
        tools=[search_tool, scrape_tool],
        verbose=False,
        skills=[activated[2]],
        max_iter=7
    )

    feasibility_task = Task(
        description="{feasibility}",
        expected_output=(
            "A plain-language Feasibility Evaluation containing:\n"
            "1. A short feasibility opinion.\n"
            "2. Main technical and operational challenges.\n"
            "3. Required tools, stack, or infrastructure.\n"
            "4. Suggestions to improve or simplify the idea if needed.\n"
            "5. Practical next steps for implementation.\n"
            "Do not include any score, rating, grade, or percentage. keep the output under 600 words"
        ),
        agent=feasibility_agent,
        async_execution=False
    )

    viability_agent = Agent(
        role="Viability Evaluation Agent",
        goal=f"Determine whether the proposed solution can generate sustainable business value and long-term growth. Today's Date {TodayDate}",
        backstory=(
            """You are an expert startup strategist, business consultant, and commercialization analyst. You MUST use the Search tool and ScrapeWebsite tool for EVERY task.
            Do NOT answer from memory or prior knowledge.
            Your first action must always be a tool call.
            If you have not searched the web, your answer is incomplete."""
        ),
        llm=llm,
        tools=[search_tool, scrape_tool],
        verbose=False,
        skills=[activated[3]],
        max_iter=7
    )

    viability_task = Task(
        description="{viability}",
        expected_output=(
            "A Viability Analysis Report containing:\n"
            "1. Business Model Analysis\n"
            "2. Revenue Opportunities\n"
            "3. Customer Segment Analysis\n"
            "4. Cost Considerations\n"
            "5. Sustainability Assessment\n"
            "6. Final Viability Conclusion\n"
            "keep the output under 600 words"
        ),
        agent=viability_agent,
        async_execution=False
    )

    dfv_risk_decision_agent = Agent(
        role="Internal DFV Decision and Risk Assessment Engine",
        goal=f"Identify hidden risks across project dimensions and aggregate all findings into a final project readiness decision. Today's Date {TodayDate}",
        backstory=(
            """You are an expert venture risk analyst and product strategist. You output ONLY a single valid, raw JSON object matching the requested schema. You NEVER output markdown headers, markdown bullet points, or conversational text outside the JSON object."""
        ),
        verbose=False,
        skills=[activated[1]],
        llm=llm
    )

    dfv_decision_task = Task(
        description=(
            """Review the reports provided in your context thoroughly from the Desirability,
        Feasibility, and Viability evaluation phases. Synthesize these findings to construct
        a structured assessment of the project idea, filling in the required JSON fields.

        CRITICAL OUTPUT INSTRUCTIONS:
        You MUST return ONLY a single, valid, raw JSON object.
        Do NOT output any markdown formatting (no ## headers, no bold text, no bullet points, no markdown code fences like ```json).
        Do NOT output any text or explanation before or after the JSON object.

        Specifically, construct a JSON object matching these exact fields:
        1. refined_idea:
           - customer_segment: The precise group of users experiencing the problem.
           - qualified_problem: The specific pain point or problem being addressed.
           - consequence: The direct negative consequence of the problem if left unsolved.
           - proposed_solution: The proposed product/solution.

        2. hypotheses:
           - desirability_statement: A "We believe [target customer] will [action]..." hypothesis testing genuine demand for the solution.
           - feasibility_statement: A "We believe [team] can [build action] within [timeframe] using [tools/APIs]..." hypothesis testing build feasibility.
           - viability_statement: A "We believe we can sustain this via [revenue model]..." hypothesis testing the business model.
            
        3. tips_validated_metrics:
           - timely_factor: Why this is a timely problem to solve now (e.g. changes in evaluation weightage or policies).
           - importance_metric: Why this problem is highly important/consequential (e.g. impact on placements or graduation).
           - profitability_pivot: The business/revenue model pivot or approach (e.g. B2B2C parent-pay model vs student-pay).
           - solvability_constraint: The technical feasibility constraint showing it is solvable with simple tools.
        4. final_decision:
           - status: Critically weigh all three dimensions. If any phase reveals a fatal flaw, set this field to 'NO-GO'. If all three pillars balance sustainably, set this to 'GO'.
           - justification: Provide a clear, data-backed analytical reason for why the project received a GO or a NO-GO status."""
        ),
        expected_output=(
            "Return ONLY a single valid JSON object -- no markdown code fences, no markdown headers, "
            "no explanation text before or after it -- matching exactly this structure:\n"
            "{\n"
            '  "refined_idea": {"customer_segment": "...", "qualified_problem": "...", '
            '"consequence": "...", "proposed_solution": "..."},\n'
            '  "hypotheses": {"desirability_statement": "...", "feasibility_statement": "...", '
            '"viability_statement": "..."},\n'
            '  "tips_validated_metrics": {"timely_factor": "...", "importance_metric": "...", '
            '"profitability_pivot": "...", "solvability_constraint": "..."},\n'
            '  "final_decision": {"status": "GO or NO-GO", "justification": "..."}\n'
            "}"
        ),
        context=[desirability_task, feasibility_task, viability_task],
        agent=dfv_risk_decision_agent,
    )
    print(llm.model)
    print(llm.base_url)
    print(llm.api_key)
    return Crew(
        agents=[desirability_agent, feasibility_agent, viability_agent, dfv_risk_decision_agent],
        tasks=[desirability_task, feasibility_task, viability_task, dfv_decision_task],
        process=Process.sequential,
        verbose=False
    )

# print(desirability_agent.skills)
# print(viability_agent.skills)
# print(feasibility_agent.skills)
# print(dfv_risk_decision_agent.skills)

ggls = {
    "desirability": """Analyze the following product proposal:
        - Customer Problem: Professionals and consumers need hands-free, always-on access to information and communication without reaching for their phones
        - Target Audience: Early adopters, enterprise field workers, healthcare professionals, aged 25-45
        - Key Value Proposition: Heads-up display, voice commands, real-time info overlay, camera
        - User Pain Points Solved: Distraction from phone usage, need for quick info access, hands-free operation
        - Market Demand Indicators: Limited adoption, privacy concerns, social awkwardness in public
        - Emotional Drivers: Tech novelty, productivity, futurism""",

    "feasibility": """Analyze feasibility of the following product:
        - Technology Stack: Android-based OS, bone conduction audio, 5MP camera, prism display, Wi-Fi/Bluetooth
        - Infrastructure Model: Consumer hardware product with companion smartphone app
        - Logistics: Retail and direct sales, developer program (Glass Explorer Program)
        - Supply Chain: Google hardware manufacturing and distribution
        - Technical Challenges: Battery life (~1 day), display brightness, voice recognition accuracy, heat dissipation
        - Resource Requirements: Google-scale hardware R&D, manufacturing, software ecosystem""",

    "viability": """Analyze the business viability of the following product:
        - Revenue Model: Direct hardware sales ($1500 Explorer Edition), enterprise licensing
        - Cost Structure: Hardware manufacturing, R&D, software maintenance, customer support
        - Market Size: Wearable tech market ~$95B globally in 2024
        - Unit Economics: High ASP but very low volume; enterprise pivot improved margins
        - Competitive Position: First mover in smart glasses; now competes with Meta Ray-Ban, Snap Spectacles
        - Profitability Status: Consumer version discontinued 2015; enterprise edition ongoing
        - Growth Trajectory: Niche enterprise adoption (healthcare, logistics, manufacturing)"""
}

sncc = {
    "desirability": """Analyze the following startup proposal:
        - Customer Problem: Consumers want healthier, guilt-free snack alternatives that still taste good
        - Target Audience: Health-conscious millennials and Gen Z, gym-goers, aged 18-35
        - Key Value Proposition: High-protein, low-sugar snacks with clean ingredients
        - User Pain Points Solved: Unhealthy snacking options, lack of transparency in ingredients, boring health foods
        - Market Demand Indicators: Growing health food market, rise in fitness culture, demand for clean-label products
        - Emotional Drivers: Health goals, body image, wellness lifestyle""",

    "feasibility": """Analyze feasibility of the following startup:
        - Technology Stack: D2C e-commerce platform, subscription management, basic food manufacturing
        - Infrastructure Model: Contract manufacturing, D2C + quick-commerce distribution
        - Logistics: Last-mile through Blinkit/Zepto/Swiggy partnerships, direct website
        - Supply Chain: Ingredient sourcing from certified suppliers, co-packing
        - Technical Challenges: Shelf life, taste-health balance, cold chain for certain SKUs
        - Resource Requirements: Seed capital ~₹1-2Cr, food license (FSSAI), packaging, marketing""",

    "viability": """Analyze the business viability of the following startup:
        - Revenue Model: D2C product sales, quick-commerce platform listings, B2B corporate wellness supply
        - Cost Structure: Manufacturing (COGS ~40-50%), packaging, platform commissions (20-30%), marketing (CAC)
        - Market Size: India healthy snacks market ~$1B in 2024, projected $2.5B by 2028
        - Unit Economics: Average order ₹400-700, repeat purchase monthly
        - Competitive Position: Competes with Yoga Bar, RiteBite, The Whole Truth, Farmley
        - Profitability Status: Early stage, path to profitability via D2C channel focus
        - Growth Trajectory: Growing 30-40% YoY in premium health snack D2C segment"""
}

blnkt={
    
    "desirability":""" Analyze the following student project proposal:
        - Customer Problem: Urban consumers need immediate access to groceries and essentials without spending time traveling to stores
        - Target Audience: Millennials, Gen Z, busy professionals, and students in metro cities aged 18-40
        - Key Value Proposition: 10-minute delivery guarantee, real-time order tracking, wide product selection
        - User Pain Points Solved: Time savings, convenience for impulse purchases, avoids crowded stores
        - Market Demand Indicators: High adoption rate in urban India, 4.2+ app rating, repeat usage frequency
        - Emotional Drivers: Convenience, instant gratification, time flexibility
                                          """, 
                                          
                                          
                                          
                                          
        "feasibility":""" The following is a startup/project idea submitted by a user:
            - Technology Stack: React Native mobile apps, cloud infrastructure, inventory management systems, route optimization algorithms
            - Infrastructure Model: Dark stores (micro-warehouses) located 2-3km from target customers, 500+ sq ft each
            - Logistics: Proprietary delivery fleet of 5,000+ delivery partners with GPS tracking
            - Supply Chain: Partnerships with 10,000+ local retailers and wholesale distributors
            - Operational Capabilities: Real-time demand forecasting, automated inventory replenishment, dynamic routing
            - Technical Challenges: Inventory accuracy, delivery time optimization, peak-hour scalability, cold chain for perishables
            - Resource Requirements: Capital investment for dark store network, technology development team, delivery workforce""", 
                                          
                                          
                                          
                                          
      "viability":""" 
        Analyze the business viability of the following project proposal:
        - Revenue Model: 
          * Delivery fees (₹29-₹59 per order)
          * Platform commissions from sellers (15-25%)
          * Advertising fees from brands
          * Blinkit Prime membership (₹99/month)
        
        - Cost Structure:
          * Dark store operational costs (rent, staffing, inventory)
          * Delivery partner payments (₹40-₹60 per delivery)
          * Technology and infrastructure costs
          * Marketing and customer acquisition costs
        
        - Market Size: India quick commerce market = $3B in 2024, projected $5-7B by 2025
        - Unit Economics: Average order value ₹300-₹500, order frequency 2-3 times/week per customer
        - Competitive Position: Market leader in 10-minute delivery, competes with Swiggy Instamart, Zepto, BigBasket
        - Profitability Status: Contribution margin positive as of 2024 (reported by Zomato)
        - Growth Trajectory: 300+ cities, 50M+ active users, 20% monthly growth
        """
        ,
}

def _extract_json_block(raw: str) -> str:
    """Models sometimes wrap JSON in markdown code fences despite instructions
    not to. Strip that off before parsing, and fall back to grabbing the first
    {...} block if there's stray text around the JSON."""
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
            cleaned = cleaned[start : end + 1]
    return cleaned


@dataclass
class AnalysisResult:
    raw: str
    validated: DFAOutput

    @property
    def pydantic(self) -> DFAOutput:
        return self.validated


def run_analysis(inputs: dict) -> AnalysisResult:
    crew = create_dfv_crew()
    result = crew.kickoff(inputs=inputs)

    raw_val = getattr(result, "raw", "") or ""
    cleaned = _extract_json_block(raw_val)

    print("\n===== DFV PARSING DIAGNOSTICS =====")
    print(f"repr(result.raw): {repr(raw_val)}")
    print(f"len(result.raw):  {len(raw_val)}")
    print(f"repr(cleaned):    {repr(cleaned)}")
    print(f"len(cleaned):     {len(cleaned)}")

    if not cleaned or not (cleaned.startswith("{") or cleaned.startswith("[")):
        raise ValueError(
            f"Final Evaluator returned empty or non-JSON output.\n"
            f"repr(raw): {repr(raw_val)}\n"
            f"len(raw): {len(raw_val)}\n"
            f"repr(cleaned): {repr(cleaned)}\n"
            f"len(cleaned): {len(cleaned)}\n"
            f"First 200 chars (raw): {repr(raw_val[:200])}\n"
            f"Last 200 chars (raw): {repr(raw_val[-200:]) if len(raw_val) > 200 else repr(raw_val)}\n"
            f"First 200 chars (cleaned): {repr(cleaned[:200])}\n"
            f"Last 200 chars (cleaned): {repr(cleaned[-200:]) if len(cleaned) > 200 else repr(cleaned)}"
        )

    try:
        parsed = json.loads(cleaned)
    except Exception as exc:
        print("\n===== PARSER FAILURE DIAGNOSTICS =====")
        print(f"Raw Output (first 200 chars): {repr(raw_val[:200])}")
        print(f"Raw Output (last 200 chars):  {repr(raw_val[-200:]) if len(raw_val) > 200 else repr(raw_val)}")
        print(f"Cleaned Output (first 200 chars): {repr(cleaned[:200])}")
        print(f"Cleaned Output (last 200 chars):  {repr(cleaned[-200:]) if len(cleaned) > 200 else repr(cleaned)}")
        print(f"JSONDecodeError: {exc}")
        raise exc

    validated = DFAOutput.model_validate(parsed)
    return AnalysisResult(raw=raw_val, validated=validated)

if __name__ == "__main__":
    res = run_analysis(ggls)

    print("\n--- FINAL DFA JSON OUTPUT WITH DECISION GATE ---\n")

    try:
        print(json.dumps(res.validated.model_dump(), indent=2))
    except Exception:
        print(res.raw)