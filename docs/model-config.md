# Model Configuration

This document describes the LLM models and configuration used across all agents in the AGIS platform.

---

## TIPSC Agent

| Setting | Value |
|---------|-------|
| **Model** | `bonsai-8b` (served via LM Studio) |
| **Endpoint** | `http://127.0.0.1:1234/v1` |
| **Temperature** | `0.1` |
| **Max Tokens** | `4096` |
| **Framework** | CrewAI with sequential/parallel task execution |
| **System Prompt** | Embedded in `TIPSC-Agent/src/agents/` |
| **Tools** | RAG retrieval (pinecone/local), web search (criteria evaluation |

---

## DFV Agent (Desirability/Feasibility/Viability)

| Setting | Value |
|---------|-------|
| **Model** | `mistral-7b-instruct` (served via LM Studio) |
| **Endpoint** | `http://127.0.0.1:1234/v1` |
| **Temperature** | `0.2` |
| **Max Tokens** | `4096` |
| **Framework** | CrewAI with 3 parallel sub-agents |
| **System Prompt** | Embedded in `dfv-agent/src/agents/` |
| **Tools** | Financial modeling calculator, market data lookup |

---

## Discovery Agent (Customer Interview Planner)

| Setting | Value |
|---------|-------|
| **Model** | `mistral-7b-instruct` (served via LM Studio) |
| **Endpoint** | `http://127.0.0.1:1234/v1` |
| **Temperature** | `0.3` |
| **Max Tokens** | `4096` |
| **Framework** | CrewAI with JTBD specialist + interview planner |
| **System Prompt** | Embedded in `customer-interview-planner-agent/src/agents/` |
| **Tools** | None (pure reasoning) |

---

## LM Studio Setup

1. Download and install LM Studio
2. Load models:
   - `bonsai-8b` for TIPSC
   - `mistral-7b-instruct` for DFV & Discovery
3. Enable **Local Server** on port `1234`
4. Verify: `curl http://127.0.0.1:1234/v1/models`

---

## Environment Variables

### Backend (.env)
```
LM_STUDIO_URL=http://127.0.0.1:1234/v1
TIPSC_MODEL=bonsai-8b
DFV_MODEL=mistral-7b-instruct
DISCOVERY_MODEL=mistral-7b-instruct
```

### Workers (.env)
```
LM_STUDIO_URL=http://127.0.0.1:1234/v1
LM_STUDIO_MODEL=bonsai-8b  # TIPSC worker
# or
LM_STUDIO_MODEL=mistral-7b-instruct  # Combined worker
```

---

## Model Selection Rationale

| Agent | Model | Why |
|-------|-------|-----|
| TIPSC | Bonsai-8B | Fine-tuned for structured evaluation tasks, follows rubric precisely |
| DFV | Mistral-7B | Strong reasoning for business analysis, financial modeling |
| Discovery | Mistral-7B | Creative JTBD generation, interview question design |

---

## Token Limits & Timeouts

| Agent | Max Tokens | Timeout (seconds) |
|-------|------------|-------------------|
| TIPSC | 4096 | 900 (15 min) |
| DFV | 4096 | 1200 (20 min) |
| Discovery | 4096 | 600 (10 min) |

Workers enforce timeouts and will fail the flow if exceeded (error code: `CREWAI_TIMEOUT`).

---

## Prompt Versioning

All system prompts are versioned in the agent source code:
- `TIPSC-Agent/src/agents/v1_prompts.py`
- `dfv-agent/src/agents/v1_prompts.py`
- `customer-interview-planner-agent/src/agents/v1_prompts.py`

When prompts change, bump the `schema_version` in Kafka payloads.