# Sequence Diagrams

This document contains Mermaid sequence diagrams for the key workflows in the AGIS platform.

---

## 1. Session Creation & TIPSC Trigger

```mermaid
sequenceDiagram
    actor Student
    participant Frontend
    participant Backend as FastAPI Backend
    participant MongoDB
    participant Kafka
    participant TIPSCWorker as TIPSC Worker

    Student->>Frontend: Fill pre-evaluation form
    Frontend->>Backend: POST /api/v1/sessions<br/>{problem_statement, customer_segment, ...}<br/>Idempotency-Key: uuid
    Backend->>MongoDB: INSERT session (status: created)
    Backend->>Kafka: PUBLISH userSession.tipsc<br/>{session_id, student_id, correlation_id, ...}
    Backend->>MongoDB: UPDATE session (status: queued)
    Backend-->>Frontend: 201 Created {session_id, status: queued}
    
    par Worker Processing
        Kafka->>TIPSCWorker: CONSUME userSession.tipsc
        TIPSCWorker->>MongoDB: UPDATE session (status: tipsc_running)
        TIPSCWorker->>TIPSCWorker: Run CrewAI TIPSC pipeline
        TIPSCWorker->>MongoDB: UPDATE session (tipsc output, status: tipsc_completed)
        TIPSCWorker->>Kafka: PUBLISH userSession.notifications
    end
    
    loop Polling (every 5s)
        Frontend->>Backend: GET /api/v1/sessions/{id}
        Backend->>MongoDB: FIND session
        Backend-->>Frontend: 200 OK {session with tipsc output}
    end
```

---

## 2. TIPSC Follow-up Loop

```mermaid
sequenceDiagram
    actor Student
    participant Frontend
    participant Backend as FastAPI Backend
    participant MongoDB
    participant Kafka
    participant TIPSCWorker as TIPSC Worker

    Note over Student, TIPSCWorker: TIPSC completed, needs_followup=true
    Frontend->>Backend: GET /api/v1/sessions/{id}
    Backend-->>Frontend: {tipsc: {needs_followup: true, pending_question: "..."}}
    Frontend->>Student: Show follow-up question
    Student->>Frontend: Enter answer
    Frontend->>Backend: POST /api/v1/sessions/{id}/followup<br/>{answer: "..."}
    Backend->>MongoDB: UPDATE session (followup_history + answer)
    Backend->>Kafka: PUBLISH userSession.tipsc (re-eval)
    Backend->>MongoDB: UPDATE session (status: tipsc_running)
    Backend-->>Frontend: 202 Accepted {status: running}
    
    Kafka->>TIPSCWorker: CONSUME re-eval event
    TIPSCWorker->>MongoDB: UPDATE session (status: tipsc_running)
    TIPSCWorker->>TIPSCWorker: Run TIPSC re-evaluation
    TIPSCWorker->>MongoDB: UPDATE session (tipsc output, needs_followup: false, status: tipsc_completed)
```

---

## 3. DFV Flow

```mermaid
sequenceDiagram
    actor Student
    participant Frontend
    participant Backend as FastAPI Backend
    participant MongoDB
    participant Kafka
    participant DFVWorker as DFV Worker (Combined)

    Student->>Frontend: Click "Start DFV", fill context
    Frontend->>Backend: POST /api/v1/sessions/{id}/trigger/dfv<br/>{desirability_context, feasibility_context, viability_context}
    Backend->>MongoDB: VALIDATE session status == tipsc_completed && ready_for_dfv
    Backend->>Kafka: PUBLISH userSession.dfv<br/>{session_id, dfv_inputs, correlation_id}
    Backend->>MongoDB: UPDATE session (status: dfv_waiting)
    Backend-->>Frontend: 202 Accepted {status: queued}
    
    Kafka->>DFVWorker: CONSUME userSession.dfv
    DFVWorker->>MongoDB: UPDATE session (status: dfv_running)
    DFVWorker->>DFVWorker: Run 3 parallel CrewAI agents<br/>(Desirability, Feasibility, Viability)
    DFVWorker->>DFVWorker: Run Evaluation Agent (GO/NO-GO)
    DFVWorker->>MongoDB: UPDATE session (dfv output, status: dfv_completed)
    DFVWorker->>Kafka: PUBLISH userSession.notifications
```

---

## 4. Discovery Flow

```mermaid
sequenceDiagram
    actor Student
    participant Frontend
    participant Backend as FastAPI Backend
    participant MongoDB
    participant Kafka
    participant DiscoveryWorker as Discovery Worker (Combined)

    Student->>Frontend: Click "Start Discovery"
    Frontend->>Backend: POST /api/v1/sessions/{id}/trigger/discovery
    Backend->>MongoDB: VALIDATE session status == dfv_completed
    Backend->>Kafka: PUBLISH userSession.discovery<br/>{session_id, correlation_id}
    Backend->>MongoDB: UPDATE session (status: discovery_waiting)
    Backend-->>Frontend: 202 Accepted {status: queued}
    
    Kafka->>DiscoveryWorker: CONSUME userSession.discovery
    DiscoveryWorker->>MongoDB: UPDATE session (status: discovery_running)
    DiscoveryWorker->>DiscoveryWorker: Run JTBD + Interview Planner agents
    DiscoveryWorker->>MongoDB: UPDATE session (discovery output, status: completed)
    DFVWorker->>Kafka: PUBLISH userSession.notifications
```

---

## 5. Worker Failure & Retry

```mermaid
sequenceDiagram
    participant Kafka
    participant Worker as Worker (TIPSC/DFV/Discovery)
    participant MongoDB
    participant Backend as FastAPI Backend

    Kafka->>Worker: CONSUME message
    Worker->>MongoDB: UPDATE session (status: *_running)
    Worker->>Worker: Execute CrewAI pipeline
    alt Success
        Worker->>MongoDB: UPDATE session (output, status: *_completed)
        Worker->>Kafka: PUBLISH notification
    else Failure (retry < max)
        Worker->>Worker: Wait exponential backoff
        Worker->>Kafka: REQUEUE message (same topic)
    else Failure (max retries exceeded)
        Worker->>MongoDB: UPDATE session (status: *_failed, error: "...")
        Worker->>Backend: POST /internal/sessions/{id}/failure<br/>{error_code, error_message, retry_count}
        Backend->>MongoDB: UPDATE session (status: *_failed, audit log)
        Backend->>Kafka: PUBLISH failure notification
    end
```

---

## 6. Mentor Comment Flow

```mermaid
sequenceDiagram
    actor Mentor
    participant Frontend
    participant Backend as FastAPI Backend
    participant MongoDB
    participant Kafka

    Mentor->>Frontend: View session, add comment
    Frontend->>Backend: POST /api/v1/sessions/{id}/comments<br/>{comment: "..."}
    Backend->>Backend: RBAC check (mentor + supervised team)
    Backend->>MongoDB: INSERT mentor_comments
    Backend->>MongoDB: INSERT audit_logs (COMMENT_ADDED)
    Backend-->>Frontend: 201 Created {comment_id, ...}
```

---

## 7. Authentication Flow

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Backend as FastAPI Backend
    participant PESAuth as PES Auth API
    participant MongoDB

    User->>Frontend: Enter SRN + Password
    Frontend->>Backend: POST /api/v1/auth/login<br/>{srn, password}
    Backend->>PESAuth: POST /auth/verify
    PESAuth-->>Backend: 200 {name, role, ...}
    Backend->>MongoDB: UPSERT user document
    Backend->>Backend: Generate JWT (access: 15m, refresh: 7d)
    Backend->>MongoDB: INSERT refresh_token (hashed)
    Backend-->>Frontend: 200 {access_token, refresh_token, role, user}
    
    Note over Frontend, Backend: Subsequent requests
    Frontend->>Backend: GET /api/v1/sessions<br/>Authorization: Bearer <access_token>
    Backend->>Backend: Verify JWT, extract claims
    Backend->>MongoDB: Query sessions (with RBAC filter)
    Backend-->>Frontend: 200 {data: [...], pagination: ...}
```

---

## 8. Token Refresh

```mermaid
sequenceDiagram
    actor Frontend
    participant Backend as FastAPI Backend
    participant MongoDB

    Frontend->>Backend: POST /api/v1/auth/refresh<br/>{refresh_token}
    Backend->>MongoDB: FIND refresh_token (hashed)
    alt Valid & Not Expired
        Backend->>MongoDB: DELETE old refresh_token
        Backend->>Backend: Generate new access_token + new refresh_token
        Backend->>MongoDB: INSERT new refresh_token (hashed)
        Backend-->>Frontend: 200 {access_token, refresh_token, expires_in}
    else Invalid/Expired
        Backend-->>Frontend: 401 {code: REFRESH_TOKEN_INVALID/EXPIRED}
    end
```

---

## 9. Archive Session

```mermaid
sequenceDiagram
    actor Student
    participant Frontend
    participant Backend as FastAPI Backend
    participant MongoDB
    participant Kafka

    Student->>Frontend: Click "Archive Session"
    Frontend->>Backend: DELETE /api/v1/sessions/{id}
    Backend->>MongoDB: VALIDATE status NOT IN (running states)
    Backend->>MongoDB: UPDATE session (status: archived, archived_at: now)
    Backend->>MongoDB: INSERT audit_logs (SESSION_ARCHIVED)
    Backend-->>Frontend: 200 {session with status: archived}
```

---

## Diagram Rendering

These diagrams are written in [Mermaid](https://mermaid.js.org/) syntax. Render them in:
- GitHub/GitLab markdown
- VS Code with Mermaid extension
- Notion, Obsidian, or any Mermaid-compatible viewer
- [Mermaid Live Editor](https://mermaid.live/)