# Flow Shapes — Request/Response Payloads

This document defines the exact JSON shapes for all flow inputs and outputs. These are the canonical contracts between the backend, workers, and frontend.

---

## 1. Session Creation (POST /sessions)

### Request

```json
{
  "problem_statement": "string (20-5000 chars)",
  "customer_segment": "string (2-2000 chars)",
  "consequence": "string (2-3000 chars)",
  "assumptions": ["string"],
  "proposed_solution": "string (10-3000 chars)",
  "target_geography": "string (2-1000 chars)",
  "industry_sector": "string (2-1000 chars)",
  "team_id": "string (optional)"
}
```

### Response (201)

```json
{
  "data": {
    "session_id": "ses_01J2K...",
    "student_id": "usr_01J2K...",
    "team_id": "team_01J2K...",
    "problem_statement": "...",
    "customer_segment": "...",
    "consequence": "...",
    "assumptions": [...],
    "proposed_solution": "...",
    "target_geography": "...",
    "industry_sector": "...",
    "status": "queued",
    "version": 1,
    "preeval": null,
    "validation": null,
    "regulatory": null,
    "ethics": null,
    "compliance_context": null,
    "tipsc": null,
    "dfv": null,
    "discovery": null,
    "pending_question": null,
    "followup_turn": 0,
    "followup_history": [],
    "correlation_id": "cor_01J2K...",
    "error": null,
    "rejection_reason": null,
    "created_at": "2026-06-01T10:00:00Z",
    "updated_at": "2026-06-01T10:00:00Z",
    "archived_at": null
  }
}
```

---

## 2. TIPSC Trigger (POST /sessions//trigger/tipsc)

### Request

```json
{}
```

### Response (202)

```json
{
  "data": {
    "session_id": "ses_01J2K...",
    "flow": "tipsc",
    "status": "queued",
    "correlation_id": "cor_01J2K...",
    "triggered_at": "2026-06-01T10:00:00Z"
  }
}
```

---

## 3. TIPSC Follow-up (POST /sessions/followup)

### Request

```json
{
  "answer": "string (1-5000 chars)"
}
```

### Response (202)

```json
{
  "data": {
    "session_id": "ses_01J2K...",
    "flow": "tipsc",
    "status": "running",
    "correlation_id": "cor_01J2K...",
    "triggered_at": "2026-06-01T10:15:00Z"
  }
}
```

---

## 4. TIPSC Output (Worker → MongoDB / Internal API)

### Kafka Payload (userSession.tipsc)

```json
{
  "event_id": "evt_01J2K...",
  "correlation_id": "cor_01J2K...",
  "session_id": "ses_01J2K...",
  "team_id": "team_01J2K...",
  "student_id": "usr_01J2K...",
  "flow": "tipsc",
  "timestamp": "2026-06-01T10:00:00Z",
  "schema_version": "1.0",
  "payload": {
    "problem_statement": "...",
    "customer_segment": "...",
    "consequence": "...",
    "assumptions": [...],
    "proposed_solution": "...",
    "target_geography": "...",
    "industry_sector": "..."
  }
}
```

### Worker Output (POST /internal/sessions//output)

```json
{
  "flow": "tipsc",
  "correlation_id": "cor_01J2K...",
  "status": "completed",
  "output": {
    "tips_rag_scores": {
      "T": "Strong timing - market is ready",
      "I": "Unique angle on mentorship",
      "P": "Well-defined problem",
      "S": "Feasible solution",
      "T_reason": "EdTech growth post-COVID...",
      "I_reason": "Niche focus on Tier-2...",
      "P_reason": "Clear pain point...",
      "S_reason": "Technical feasibility high..."
    },
    "refined_idea": {
      "customer_segment": "Engineering students in Tier-2/3 cities",
      "qualified_problem": "No accessible mentor network",
      "consequence": "Ideas die before validation",
      "proposed_solution": "Async video mentorship platform"
    },
    "solution_alignment": "Strong alignment...",
    "overall_readiness": "Ready for DFV",
    "ready_for_dfv": true,
    "needs_followup": false,
    "missing_criteria": [],
    "criteria_state": {},
    "compliance_flag": true,
    "reasoning": "The idea is timely given the growth in EdTech...",
    "followups_asked": 1,
    "completed_at": "2026-06-01T10:05:00Z"
  },
  "duration_seconds": 287,
  "worker_id": "tipsc-worker-01"
}
```

### Embedded in Session Document

```json
{
  "tipsc": {
    "tips_rag_scores": { ... },
    "refined_idea": { ... },
    "solution_alignment": "...",
    "overall_readiness": "...",
    "ready_for_dfv": true,
    "needs_followup": false,
    "missing_criteria": [],
    "criteria_state": {},
    "compliance_flag": true,
    "reasoning": "...",
    "followups_asked": 1,
    "completed_at": "2026-06-01T10:05:00Z"
  }
}
```

---

## 5. DFV Trigger (POST /sessions//trigger/dfv)

### Request

```json
{
  "desirability_context": "string (100-3000 chars)",
  "feasibility_context": "string (100-3000 chars)",
  "viability_context": "string (100-3000 chars)"
}
```

### Response (202)

```json
{
  "data": {
    "session_id": "ses_01J2K...",
    "flow": "dfv",
    "status": "queued",
    "correlation_id": "cor_01J2K...",
    "triggered_at": "2026-06-01T10:10:00Z"
  }
}
```

---

## 6. DFV Output (Worker → MongoDB / Internal API)

### Kafka Payload (userSession.dfv)

```json
{
  "event_id": "evt_01J2K...",
  "correlation_id": "cor_01J2K...",
  "session_id": "ses_01J2K...",
  "team_id": "team_01J2K...",
  "student_id": "usr_01J2K...",
  "flow": "dfv",
  "timestamp": "2026-06-01T10:10:00Z",
  "schema_version": "1.0",
  "payload": {
    "desirability_context": "...",
    "feasibility_context": "...",
    "viability_context": "...",
    "tipsc_output": { ... }
  }
}
```

### Worker Output

```json
{
  "flow": "dfv",
  "correlation_id": "cor_01J2K...",
  "status": "completed",
  "output": {
    "desirability": {
      "score": 8,
      "report": "Strong customer validation evidence...",
      "recommendations": []
    },
    "feasibility": {
      "score": 7,
      "report": "Technical stack is appropriate...",
      "recommendations": ["Consider timeline buffer for API integration"]
    },
    "viability": {
      "score": 6,
      "report": "Revenue model is sound but...",
      "recommendations": ["Validate pricing with a paid pilot"]
    },
    "overall_decision": "GO",
    "summary": "The idea shows strong market pull...",
    "json_report": {}
  },
  "duration_seconds": 412,
  "worker_id": "dfv-worker-01"
}
```

### Embedded in Session Document

```json
{
  "dfv": {
    "correlation_id": "cor_01J2K...",
    "status": "completed",
    "output": {
      "desirability": { "score": 8, "report": "...", "recommendations": [] },
      "feasibility": { "score": 7, "report": "...", "recommendations": [...] },
      "viability": { "score": 6, "report": "...", "recommendations": [...] },
      "overall_decision": "GO",
      "summary": "...",
      "json_report": {}
    },
    "error": null,
    "retry_count": 0,
    "started_at": "2026-06-01T10:10:00Z",
    "completed_at": "2026-06-01T10:17:00Z",
    "idea_name": "MentorConnect"
  }
}
```

---

## 7. Discovery Trigger (POST /sessions//trigger/discovery)

### Request

```json
{
  "discovery_inputs": "string (optional)"
}
```

### Response (202)

```json
{
  "data": {
    "session_id": "ses_01J2K...",
    "flow": "discovery",
    "status": "queued",
    "correlation_id": "cor_01J2K...",
    "triggered_at": "2026-06-01T10:30:00Z"
  }
}
```

---

## 8. Discovery Output (Worker → MongoDB / Internal API)

### Kafka Payload (userSession.discovery)

```json
{
  "event_id": "evt_01J2K...",
  "correlation_id": "cor_01J2K...",
  "session_id": "ses_01J2K...",
  "team_id": "team_01J2K...",
  "student_id": "usr_01J2K...",
  "flow": "discovery",
  "timestamp": "2026-06-01T10:30:00Z",
  "schema_version": "1.0",
  "payload": {
    "dfv_output": { ... }
  }
}
```

### Worker Output

```json
{
  "flow": "discovery",
  "correlation_id": "cor_01J2K...",
  "status": "completed",
  "output": {
    "jtbd_elements": [
      {
        "job": "Find a mentor who understands my domain",
        "outcome": "Match with a mentor in EdTech within 24 hours",
        "pain": "No local networks for niche domains"
      }
    ],
    "interview_plan": {
      "target_segment": "Engineering students in Tier-2 cities",
      "interview_questions": [
        "Can you describe the last time you tried to find a mentor?",
        "What made that experience frustrating?"
      ],
      "hypothesis_to_validate": "Students are willing to pay for async video mentorship"
    }
  },
  "duration_seconds": 310,
  "worker_id": "discovery-worker-01"
}
```

### Embedded in Session Document

```json
{
  "discovery": {
    "correlation_id": "cor_01J2K...",
    "status": "completed",
    "output": {
      "jtbd_elements": [
        {
          "job": "...",
          "outcome": "...",
          "pain": "..."
        }
      ],
      "interview_plan": {
        "target_segment": "...",
        "interview_questions": [...],
        "hypothesis_to_validate": "..."
      }
    },
    "error": null,
    "retry_count": 0,
    "started_at": "2026-06-01T10:30:00Z",
    "completed_at": "2026-06-01T10:35:00Z"
  }
}
```

---

## 9. Worker Failure Output

```json
{
  "flow": "tipsc",
  "correlation_id": "cor_01J2K...",
  "error_code": "CREWAI_TIMEOUT",
  "error_message": "Agent did not respond within 15 minutes",
  "retry_count": 3,
  "worker_id": "tipsc-worker-01"
}
```

---

## 10. Session Status Values

| Status                | Description                                   |
| --------------------- | --------------------------------------------- |
| `created`           | Session created, Kafka not yet published      |
| `queued`            | Kafka event published, waiting for worker     |
| `tipsc_running`     | TIPSC worker actively processing              |
| `tipsc_completed`   | TIPSC finished successfully                   |
| `tipsc_failed`      | TIPSC failed after retries                    |
| `dfv_waiting`       | TIPSC passed, student must trigger DFV        |
| `dfv_running`       | DFV worker actively processing                |
| `dfv_completed`     | DFV finished successfully                     |
| `dfv_failed`        | DFV failed after retries                      |
| `discovery_waiting` | DFV completed, student must trigger discovery |
| `discovery_running` | Discovery worker actively processing          |
| `discovery_failed`  | Discovery failed after retries                |
| `completed`         | All flows completed successfully              |
| `archived`          | Student archived the session                  |

---

## 11. Flow Trigger Response Status Values

| Status      | When Returned                                     |
| ----------- | ------------------------------------------------- |
| `queued`  | Kafka publish succeeded, worker not yet picked up |
| `running` | Worker already picked up (idempotent re-trigger)  |
