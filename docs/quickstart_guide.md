# Quickstart Guide

> **Quickstart** is a rapid AI evaluation that combines **Ethics (3 gates)**, **TIPSC (4 dimensions)**, and **DFV (3 pillars)** into a single 10-parameter assessment. Runs in-process via CrewAI agent — no worker needed.

---

## Overview

| Aspect | Details |
|--------|---------|
| **Endpoint** | `POST /api/v1/quickstart/evaluate` |
| **Auth** | JWT Bearer token (Student, Mentor Workspace, or Admin) |
| **Duration** | ~30-60 seconds |
| **Output** | 10 parameter ratings (GREEN/YELLOW/RED) + advice + priority next steps |

---

## Request

```http
POST /api/v1/quickstart/evaluate
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "problem": "Students struggle to manage group project deadlines and contributions effectively.",
  "customer": "Software development students in their 2nd–4th year working on capstone projects.",
  "solution": "A collaborative project management tool with automated deadline tracking and contribution analytics.",
  "consequence": "Missed deadlines, failed courses, and weakened team dynamics affecting future collaboration.",
  "business_model": "Freemium SaaS: free for students, $15/month per team for advanced analytics and integrations.",
  "urgency": "Capstone season starts in 3 months; need MVP by then.",
  "hurdles": "Integration with university LMS (Canvas/Blackboard); FERPA compliance for student data."
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `problem` | string | ✅ | Core problem being solved |
| `customer` | string | ✅ | Target customer (demographics, role, context) |
| `solution` | string | ✅ | Proposed solution and how it works |
| `consequence` | string | ✅ | Consequences if problem unsolved |
| `business_model` | string | ✅ | Revenue model, pricing, who pays |
| `urgency` | string | ✅ | Why now? Timeline to launch |
| `hurdles` | string | ✅ | Biggest tech/legal/regulatory hurdles |

---

## Response

```json
{
  "input": { /* echoed input */ },
  "parameters": [
    {
      "name": "Harm Vector",
      "rating": "GREEN",
      "reason": "No significant harm vectors identified; problem is educational productivity."
    },
    {
      "name": "Legal Risk",
      "rating": "YELLOW",
      "reason": "FERPA compliance needed for student data; legal review recommended before LMS integration."
    },
    {
      "name": "Problem-Solution Integrity",
      "rating": "GREEN",
      "reason": "Solution directly addresses the stated problem with clear value proposition."
    },
    {
      "name": "Timely",
      "rating": "GREEN",
      "reason": "Capstone season creates natural deadline; market entry window is clear."
    },
    {
      "name": "Important",
      "rating": "GREEN",
      "reason": "Clear differentiation from generic PM tools via academic focus and LMS integration."
    },
    {
      "name": "Profitable",
      "rating": "YELLOW",
      "reason": "Pain point is real but severity needs validation; freemium conversion uncertain."
    },
    {
      "name": "Solvable",
      "rating": "GREEN",
      "reason": "Technically achievable with available tools; team has relevant expertise."
    },
    {
      "name": "Desirability",
      "rating": "GREEN",
      "reason": "Strong user demand validated through preliminary interviews."
    },
    {
      "name": "Feasibility",
      "rating": "GREEN",
      "reason": "Technically achievable with current team; LMS APIs are well-documented."
    },
    {
      "name": "Viability",
      "rating": "YELLOW",
      "reason": "Freemium model viable but requires LMS partnerships for distribution."
    }
  ],
  "red_count": 0,
  "yellow_count": 4,
  "green_count": 6,
  "parameter_advice": {
    "Legal Risk": "Engage university legal counsel early; draft FERPA compliance checklist before MVP.",
    "Profitable": "Run willingness-to-pay survey with 50+ target users; test pricing tiers.",
    "Viability": "Secure LOI from 2+ universities for LMS integration pilot before launch."
  },
  "priority_advice": [
    "Engage university legal counsel for FERPA compliance before MVP development.",
    "Run willingness-to-pay survey with 50+ target users to validate pricing.",
    "Secure LOI from 2+ universities for LMS integration pilot."
  ],
  "timestamp": "2026-10-22T15:30:00.123456+00:00"
}
```

---

## Response Fields

| Field | Description |
|-------|-------------|
| `parameters` | Array of 10 parameter ratings |
| `parameter[].name` | Parameter name (e.g., "Harm Vector") |
| `parameter[].rating` | `GREEN`, `YELLOW`, or `RED` |
| `parameter[].reason` | One-sentence justification |
| `red_count` | Count of RED ratings |
| `yellow_count` | Count of YELLOW ratings |
| `green_count` | Count of GREEN ratings |
| `parameter_advice` | Map of parameter → specific advice (for YELLOW/RED) |
| `priority_advice` | Top 3 priority next steps ranked by impact |
| `timestamp` | ISO 8601 timestamp |

---

## Rating Meanings

| Rating | Meaning |
|--------|---------|
| **GREEN** | Strong — no significant concerns |
| **YELLOW** | Moderate — needs attention/mitigation |
| **RED** | Weak — critical issue, must resolve before proceeding |

---

## Error Responses

| Status | Code | Message |
|--------|------|---------|
| 400 | `VALIDATION_ERROR` | Missing or invalid input fields |
| 401 | `INVALID_CREDENTIALS` | Invalid or expired token |
| 403 | `INSUFFICIENT_PERMISSIONS` | Role not authorized (student/mentor/admin only) |
| 500 | `INTERNAL_ERROR` | Agent execution failed |

---

## Usage Example (cURL)

```bash
curl -X POST http://localhost:8000/api/v1/quickstart/evaluate \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "problem": "Students struggle to manage group project deadlines...",
    "customer": "Software development students in 2nd–4th year...",
    "solution": "Collaborative PM tool with automated deadline tracking...",
    "consequence": "Missed deadlines, failed courses...",
    "business_model": "Freemium SaaS: free for students, $15/mo/team...",
    "urgency": "Capstone season starts in 3 months...",
    "hurdles": "LMS integration (Canvas/Blackboard); FERPA compliance"
  }'
```

---

## Integration Notes

- **In-process execution**: Runs directly in the FastAPI process via CrewAI — no Kafka worker needed
- **No session created**: Quickstart is standalone; does not create a session
- **In-process CrewAI**: Uses `quickstart-agent/quickstart_agent/main.py` loaded at startup
- **Token required**: Student, Mentor Workspace, or Admin role required

---

## Related Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/sessions` | Create full session (triggers full TIPSC → DFV → Discovery pipeline) |
| `GET /api/v1/sessions/{id}` | Get session status and results |
| `POST /api/v1/sessions/{id}/trigger/tipsc` | Trigger full TIPSC evaluation |
| `POST /api/v1/sessions/{id}/trigger/dfv` | Trigger DFV evaluation |
| `POST /api/v1/sessions/{id}/trigger/discovery` | Trigger Customer Discovery |

---

## Quickstart Agent Location

```
quickstart-agent/
├── quickstart_agent/
│   ├── main.py              # Entry point (run_quickstart_eval_async)
│   ├── models.py            # Input/output Pydantic models
│   └── agents/              # CrewAI agents for Ethics, TIPSC, DFV
├── pyproject.toml
└── README.md
```

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| `OPENAI_MODEL_NAME` not set | Set in `.env` (uses NVIDIA NIM by default) |
| Agent timeout (>60s) | Increase `AGENT_TIMEOUT_SECONDS` in `.env` |
| CrewAI import errors | Ensure `quickstart-agent` is in Python path |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` from project root |