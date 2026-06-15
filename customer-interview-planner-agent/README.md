# JTBD based Customer Discovery Interview Planner Agent

## Overview

This project implements a CrewAI-based agent that analyzes problem statements using the Jobs-To-Be-Done (JTBD) framework and helps build Student teams a Customer Discovery Interview Plan. 

The agent uses:

* CrewAI for orchestration
* LiteLLM as the LLM abstraction layer (this happens under-the-hood)
* Bonsai-8B as the underlying language model (LLM) locally
* LM Studio as the local OpenAI-compatible endpoint to host the Bonsai-8B model
* Skill.md files to provide domain-specific guidance to the agent
* Skill.md sourced from https://caitlind.notion.site/JTBD-Interview-Guide-Planner-2f0dc8e0af5e80a28dc7d8195bd7d4aa

The goal is to use the technology stack above to help student teams submit their Problem statement, Problem consequence, Customer(s) Segment, Assumptions, A TIPSC context and a DFV (Desirability, Feasibility, Viability) context and get the agent to give them a clear Customer Discovery Interview Plan.

---

## Features

* Accept student inputs like Problem statement, roblem consequence, Customer(s) Segment, Assumptions, A TIPSC context and a DFV (Desirability, Feasibility, Viability) context
* Extract JTBD elements
* Generate a Structure set of instructions and plan to carry out a Customer Discovery Interview
* Operates entirely on local LLMs (as of now Bonsai-8B)
* No dependency on cloud-hosted OpenAI models

---

## Technology Stack

| Component | Version      |
| --------- | ------------ |
| Python    | 3.12.x       |
| CrewAI    | 1.14.6       |
| LiteLLM   | 1.89.0       |
| Pydantic  | 2.11.0       |
| LM Studio | Local Server |
| Model     | Bonsai-8B    |

---

## Project Structure

```text
project/
│
├── main.py
├── README.md
├── requirements.txt
│
├── skills/
│   └── JTBD_SKILL.md
│
├── input/
│   └── sample_problem.json (TBD)
│
└── output/
    └── jtbd_analysis.json (TBD)
```

---

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Requirements

requirements.txt

```text
crewai==1.14.6
litellm==1.89.0
pydantic==2.11.0
```

---

## LM Studio Setup

1. Start LM Studio.
2. Load the Bonsai-8B model.
3. Enable the OpenAI-compatible API server.
4. Verify the server is running.

Example endpoint:

```text
http://localhost:1234/v1
```

---

## Environment Variables

Example:

```python
import os

os.environ["CREWAI_TESTING"] = "true"
os.environ["LITELLM_TIMEOUT"] = "1800"
os.environ["LITELLM_LOG"] = "ERROR"
os.environ["LITELLM_TELEMETRY"] = "False"
os.environ["OPENAI_API_KEY"] = "lm-studio"
```

---

## Running the Project

```bash
python main.py
```

---

## Input

The agent expects a structured problem statement JSON.

Example:

```json
{
  "problem_title": "Counterfeit Drugs in the Pharma Supply Chain",
  "problem_description": "Patients and pharmacies struggle to verify authenticity of medicines."
}
```

---

## Output (TBD)
This is how a sample output in JSON structure will look like in future.
Example:

```json
{
  "job_executor": "...",
  "core_job": "...",
  "pain_points": [],
  "desired_outcomes": []
}
```

---

## Known Issues

### LiteLLM Shutdown Logging Error

Older LiteLLM versions may display:

```text
RuntimeError: can't register atexit after shutdown
```

This was resolved after upgrading to:

```text
litellm==1.89.0
```

---

## Future Enhancements

* Enhance to accept inputs from an Agent upstream OR a direct UI Input
* Create Structured Outputs in JSON
* Memory integration (if need be for Student Teams context)
* External Vector database integration (beyond LanceDB)
* RAG-based industry context enrichment - for real world problem evaluation

---

## Author

Raghavendra Deshmukh
Adjunct Faculty – Product Management, Innovation & Entrepreneurship
PES University

```
```
