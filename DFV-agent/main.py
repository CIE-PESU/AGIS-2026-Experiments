
import os
os.environ["OPENAI_API_KEY"] = "lm-studio"
os.environ["OPENAI_API_BASE"] = "http://127.0.0.1:1234/v1"
os.environ["OPENAI_MODEL_NAME"] = "openai/bonsai-8b"
import json
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from pathlib import Path
from pydantic import BaseModel, Field
from crewai.skills import discover_skills, activate_skill
from datetime import datetime

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
    return original_supports_function_calling(self)

LLM.supports_function_calling = patched_supports_function_calling

# Load local environment files
load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
os.environ["SERPER_API_KEY"] = SERPER_API_KEY or ""

# Initialize tools required for Phase 1 Desirability market analysis
search_tool = SerperDevTool(api_key=SERPER_API_KEY)
scrape_tool = ScrapeWebsiteTool()

llm = LLM(
    model="bonsai-8b", 
    base_url="http://127.0.0.1:1234/v1", 
    api_key="lm-studio",
    temperature=0.1,
)


# Discover and activate local business framework guidelines from markdown packages
skills = discover_skills(Path("./skills"))
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

# 3. Define the Phase 1 Desirability Evaluation Agent
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

# 4. Define the Desirability Task mapped exactly to system documentation outputs
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
    async_execution=True
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
    async_execution=True
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
    async_execution=True
)

dfv_risk_decision_agent = Agent(
    role="Internal DFV Decision and Risk Assessment Engine",
    goal=f"Identify hidden risks across project dimensions and aggregate all findings into a final project readiness decision. Today's Date {TodayDate}",
    backstory=(
        """You are an expert venture risk analyst and product strategist. """
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

        Specifically:
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
    expected_output="A structured JSON object matching the DFAOutput schema including refined_idea, tips_validated_metrics, hypotheses, and final_decision properties.",
    context=[desirability_task, feasibility_task, viability_task],
    agent=dfv_risk_decision_agent,
    output_json=DFAOutput
)

# print(desirability_agent.skills)
# print(viability_agent.skills)
# print(feasibility_agent.skills)
# print(dfv_risk_decision_agent.skills)

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

crew = Crew(
    agents=[desirability_agent, feasibility_agent, viability_agent, dfv_risk_decision_agent],
    tasks=[desirability_task, feasibility_task, viability_task, dfv_decision_task],
    process=Process.sequential,
    verbose=False
)

result = crew.kickoff(inputs=blnkt)

print("\n--- FINAL DFA JSON OUTPUT WITH DECISION GATE --- \n")
try:
    print(json.dumps(json.loads(result.raw), indent=2))
except Exception:
    print(result.raw)
    