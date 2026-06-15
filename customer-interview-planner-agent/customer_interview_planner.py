from pathlib import Path
from crewai import Agent, Task, Crew, Process, LLM
from crewai.skills import discover_skills, activate_skill
import os

# Set environment variables for testing and LLM configuration
# Note that we may still see some logging errors that happen when the underlying LiteLLM tries to some clean up.
# These can be ignored for now.  
os.environ["CREWAI_TESTING"] = "true"
os.environ["LITELLM_TIMEOUT"] = "1800"
os.environ["LITELLM_LOG"] = "ERROR"
os.environ["LITELLM_TELEMETRY"] = "False"
os.environ["OPENAI_API_KEY"] = "lm-studio" 

# Define the base URL for the Local LLM
LM_URL = "http://127.0.0.1:1234/v1"

# We are using Bonsai8B as the Local LLM for this Agent
reasoning_llm = LLM(
    model="openai/bonsai-8b",
    base_url=LM_URL,
    temperature=0.2,
    max_tokens=10000,
    timeout=1800
)

# Discover all skills in a directory
skills = discover_skills(Path("./skills"))
# Activate them (loads full SKILL.md body)
activated = [activate_skill(s) for s in skills]


# This is a high level proposed structure that we will feed to the JTBD Customer Interview Planner Agent
# as an Input.  This should be the output from the earlier Agents in the Pipeline.
# Here we cover aspects like Customer Segments, Problem Statement, Consequences of the Problem
# Assumptions, Current Alternatives, Current available information, uncertainties etc.  
customer_discovery_inputs = {
  "target_customer_segment": [
    {
      "segment": "Mid-level pharmaceutical distributors",
      "role": "Primary user",
      "customer_type": "Business User"
    },
    {
      "segment": "Pharmaceutical manufacturers",
      "role": "Economic buyer",
      "customer_type": "Decision Maker"
    }
  ],

  "problem_statement": "Counterfeit medicines continue to enter the pharmaceutical supply chain. Existing QR-code based approaches are vulnerable because counterfeiters can duplicate valid codes and place them on fake products. Current verification approaches may not adequately prevent counterfeit inventory while maintaining operational efficiency.",

  "problem_consequence": [
    "Distributors face legal liability and compliance risks.",
    "Pharmacists and distributors may lose trust within the supply chain.",
    "Manufacturers suffer revenue loss and brand damage.",
    "Patients may consume ineffective or unsafe medicines.",
    "Counterfeit products undermine confidence in pharmaceutical distribution."
  ],

  "current_alternatives": [
    "Static QR codes on medicine packaging",
    "Hologram-based verification",
    "SMS verification systems",
    "Centralized tracking databases",
    "Enterprise traceability software",
    "Manual inventory inspection processes"
  ],

  "key_assumptions": [
    "Counterfeit medicines are a sufficiently important problem for distributors to actively seek better solutions.",
    "Workflow disruption is a major reason existing verification systems are not widely adopted.",
    "Distributors prefer solutions integrated into existing ERP systems rather than standalone applications.",
    "Legal liability protection is a stronger motivator than counterfeit detection itself.",
    "Manufacturers are willing to invest in improved traceability and verification capabilities.",
    "Current QR-based verification approaches are perceived as inadequate by supply-chain stakeholders."
  ],

  "what_we_already_know": [
    "The team conducted interviews with 2 distributors and 6 pharmacists.",
    "Interview feedback suggested resistance to standalone applications.",
    "Interview feedback suggested preference for integration with existing ERP systems such as Tally.",
    "The team pivoted away from a standalone verification app based on interview findings.",
    "The team believes workflow friction is a significant adoption barrier."
  ],

  "biggest_uncertainty": [
    "How important is counterfeit medicine detection relative to other operational challenges faced by distributors?",
    "What business consequences do distributors actually experience due to counterfeit products?",
    "Would distributors change their existing processes to improve counterfeit detection?",
    "What evidence would convince manufacturers to pay for improved traceability?",
    "Is legal liability protection truly the primary buying motivation?",
    "How frequently do counterfeit-related incidents occur in practice?"
  ],

  "customer_type": [
    "Business User",
    "Decision Maker"
  ],

  "proposed_solution_context": {
    "purpose": "Background context only. Do not validate directly during customer discovery interviews.",
    "summary": "A pharmaceutical traceability platform using parent-child QR relationships, ERP integration, anomaly detection and supply-chain verification to reduce counterfeit medicine circulation while minimizing workflow disruption."
  }
}

# The Customer Discovery Planner Agent
customer_discovery_planner = Agent(
    role="Customer Discovery Planner",
    goal="Help students design effective customer discovery interviews.",
    backstory="""
        You are an experienced customer discovery coach. 
        You help student entrepreneurs validate assumptions, understand customer behavior, 
        and gather evidence through interviews.
    """,
    llm=reasoning_llm,
    verbose=True,
    skills=activated #Note that we are using the SKILL.md from the skills directory
)

# The Task we are defining for the Customer Discovery Planner Agent. 
# We give it the DOs and DON'Ts of Customer Discovery Interview Planning activity that we want it to do.
# Currently it will emit a Textual Output but in the future iterations we plan to have a better structured output.
customer_discovery_task = Task(
description=f"""
You are preparing a Customer Discovery Plan
for a student startup team.

The information below represents the team's
current understanding of:

* The customer
* The problem
* The proposed solution
* Key assumptions
* Potential risks
* Existing alternatives
* Customer concerns
* Business hypotheses

IMPORTANT:

Treat all information below as hypotheses,
assumptions, or early observations.

Do not assume any statement is true.

The purpose of customer interviews is to gather
evidence that either supports or contradicts
these assumptions.

# Current Project Understanding is avaiable here: 
{customer_discovery_inputs}

Your task is to create a complete Customer Discovery Plan using the JTBD interviewing methodology available
through your skills.

Focus on discovering:
* Real customer behavior
* Actual past experiences
* Existing alternatives
* Customer motivations
* Triggers and struggling moments
* Friction and anxieties
* Evidence that validates or invalidates assumptions

STRICTLY Avoid:
* Solution pitching
* Leading questions
* Hypothetical questions
* Feature validation questions
* Asking customers what they would do in the future

Produce the following sections.
SECTION 1: CUSTOMER DISCOVERY OBJECTIVES
Identify the 4-6 most important things the team must learn from customer interviews.
For each objective explain:

* Why it matters
* Which assumptions it helps validate
* What evidence would strengthen confidence

SECTION 2: ASSUMPTION VALIDATION MATRIX
Create a table with columns:
* Assumption
* Why It Matters
* Evidence Required
* Signals To Look For

Include assumptions related to:
* Customer problem
* Importance of the problem
* Current alternatives
* Customer motivations
* Friction and barriers
* Customer anxieties
* Adoption willingness
* Business assumptions

Prioritize assumptions from highest risk to lowest risk.

SECTION 3: CUSTOMER DISCOVERY INTERVIEW GUIDE
Create a structured interview guide.
Organize questions into the following sections:

A. Warm-Up
B. Problem Exploration
C. Current Behavior
D. Struggling Moments and Triggers
E. Current Alternatives
F. Friction and Anxiety
G. Closing Reflection
STRICTLY Generate approximately 10 questions.

Questions should:
* Encourage storytelling
* Explore actual past behavior
* Reveal customer motivations
* Surface frustrations and workarounds
* Avoid leading language

SECTION 4: INTERVIEW EXECUTION GUIDE
Teach students how to conduct effective customer discovery interviews.

Include:
Before The Interview
* Preparation guidance
* Interview setup

During The Interview
* Listening techniques
* Follow-up probing techniques
* Common mistakes to avoid

After The Interview
* Documentation guidance
* Reflection guidance

Provide practical advice suitable for undergraduate entrepreneurship students.

SECTION 5: INTERVIEW RECORDING TEMPLATE
Create a reusable interview recording template.
Capture:
* Interviewee profile
* Context of discussion
* Problem evidence
* Current behavior
* Existing alternatives
* Frustrations
* Motivations
* Concerns and anxieties
* Memorable quotes
* Unexpected insights

The template should be easy for students to print and use during interviews.

SECTION 6: EVIDENCE COLLECTION CHECKLIST

Create a checklist of evidence students should return with after interviews.

Examples include:
* Examples of the problem occurring
* Evidence of current alternatives
* Evidence of consequences
* Evidence of frustration
* Evidence of willingness to change
* Evidence of adoption barriers
* Evidence that contradicts assumptions

The checklist should directly support evaluation of the assumptions identified earlier in the report.

IMPORTANT:
The purpose of the interview is NOT to validate the proposed solution.
The purpose is to understand customer behavior, current alternatives, struggling moments,
consequences, motivations and frustrations.

Avoid asking whether customers would use, purchase, test or adopt the proposed solution
unless explicitly generating a separate concept-testing section.

FINAL SUMMARY
Provide a short summary explaining:
1. The most critical assumptions to validate.
2. The biggest risks discovered so far.
3. What successful interviews should reveal.
   """,
   expected_output="""
   A complete Customer Discovery Plan containing:

1. Customer Discovery Objectives
2. Assumption Validation Matrix
3. Customer Discovery Interview Guide
4. Interview Execution Guide
5. Interview Recording Template
6. Evidence Collection Checklist
7. Final Summary

The report should be practical, student-friendly, and focused on collecting evidence rather than confirming assumptions.
""",
agent=customer_discovery_planner
)

crew = Crew(
    agents=[customer_discovery_planner],
    tasks=[customer_discovery_task],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff()

print("\n")
print("="*80)
print("Customer Discovery Plan")
print("="*80)
print(result)
