# User Journey

This document describes the complete student journey through the AGIS platform, based on the current backend implementation.

---

## Complete Journey Flow

```mermaid
flowchart TD
    A[Landing Page] --> B[Login /auth/login]
    B --> C{Role?}
    C -->|Student| D[Student Workspace]
    C -->|Mentor| E[Mentor Dashboard]
    C -->|Admin| F[Admin Dashboard]
    
    D --> G[Create New Session POST /sessions]
    G --> H{Active Session?}
    H -->|Yes| I[Archive Current First DELETE /sessions/{id}]
    I --> G
    H -->|No| J[Session Created status=queued]
    
    J --> K[Poll GET /sessions/{id} every 5s]
    K --> L{Status?}
    L -->|tipsc_running| M[Show TIPSC Loading]
    L -->|tipsc_completed| N[Show TIPSC Results]
    L -->|tipsc_failed| O[Show Error + Retry Button]
    
    N --> P[Unlock DFV Tab]
    P --> Q[Fill DFV Context POST /sessions/{id}/trigger/dfv]
    Q --> R[Poll for DFV]
    R --> S{DFV Status?}
    S -->|dfv_running| T[Show DFV Loading]
    S -->|dfv_completed| U[Show DFV Results]
    S -->|dfv_failed| V[Show Error + Retry]
    
    U --> W[Unlock Discovery Tab]
    W --> X[Trigger Discovery POST /sessions/{id}/trigger/discovery]
    X --> Y[Poll for Discovery]
    Y --> Z{Discovery Status?}
    Z -->|discovery_running| AA[Show Discovery Loading]
    Z -->|discovery_completed| BB[Show JTBD + Interview Plan]
    Z -->|discovery_failed| CC[Show Error + Retry]
    
    BB --> DD[Session Complete status=completed]
    DD --> EE[View Full Report]
    EE --> FF[Export Markdown]
    FF --> GG[Archive Session DELETE /sessions/{id}]
    GG --> D
    
    O --> K
    V --> R
    CC --> Y
```

---

## Detailed Stage Breakdown

### 1. Authentication
- **Entry Point:** `/login` page
- **Action:** Student enters SRN (format: `PES2UG22CS001`) + password
- **Backend:** `POST /api/v1/auth/login` → calls PES Auth API
- **Success:** JWT access token (15min) + refresh token (7 days) stored in localStorage
- **Redirect:** Role-based → Student → `/workspace`

### 2. Student Workspace (`/workspace`)
- **Initial State:** Check for active session via `GET /sessions/user/{student_id}/session`
- **If Active Session:** Show session status, current stage, option to archive
- **If No Session:** Show "Start New Idea" form

### 3. Create New Session
- **Form Fields:**
  - Problem Statement (min 20 chars)
  - Customer Segment (min 2 chars)
  - Consequence (min 2 chars)
  - Assumptions (array, optional)
  - Proposed Solution (min 10 chars)
  - Target Geography (min 2 chars)
  - Industry Sector (min 2 chars)
  - Team ID (optional, auto-derived)
- **Headers:** `Idempotency-Key` (UUID, required)
- **Endpoint:** `POST /api/v1/sessions`
- **Response:** Session with `status: "queued"` + `correlation_id`
- **Polling Starts:** Frontend polls `GET /api/v1/sessions/{id}` every 5 seconds

### 4. TIPSC Evaluation Phase
**Automatic Trigger:** Backend publishes to `userSession.tipsc` Kafka topic on session creation

**Frontend Shows:**
- Status badge: "Running" / "Completed" / "Failed"
- If `tipsc_completed`: Render TIPSC results
  - RAG Scores (T/I/P/S with reasoning)
  - Refined Idea (Customer, Problem, Consequence, Solution)
  - Readiness Assessment
  - `ready_for_dfv` boolean flag
  - Compliance flag
  - Follow-up questions (if `needs_followup: true`)

**Follow-up Loop (if needed):**
1. Frontend shows pending question from `session.pending_question`
2. Student submits answer via `POST /api/v1/sessions/{id}/followup`
3. Backend re-triggers TIPSC via Kafka
4. Polling continues until `needs_followup: false`

**Unlock Condition:** `tipsc_completed` AND `ready_for_dfv: true` → DFV tab enabled

### 5. DFV Analysis Phase
**Manual Trigger:** Student clicks "Start DFV Analysis" → fills context form

**DFV Context Form:**
- Desirability Context (100-3000 chars) - customer validation evidence
- Feasibility Context (100-3000 chars) - technical/build plan
- Viability Context (100-3000 chars) - business model, pricing, TAM

**Endpoint:** `POST /api/v1/sessions/{id}/trigger/dfv`
- Optional header: `Idempotency-Key`
- Backend validates: `tipsc_completed` + `ready_for_dfv: true`
- Publishes to `userSession.dfv` Kafka topic

**Polling:** Shows DFV running → completed

**DFV Results Display:**
- Three dimension scores (Desirability, Feasibility, Viability) - each 1-10
- Detailed reports per dimension
- Recommendations per dimension
- Overall Decision: `GO` or `NO-GO`
- Executive Summary

**Unlock Condition:** `dfv_completed` AND `overall_decision: "GO"` → Discovery tab enabled

### 6. Customer Discovery Planner Phase
**Manual Trigger:** Student clicks "Generate Discovery Plan"

**Endpoint:** `POST /api/v1/sessions/{id}/trigger/discovery`
- Backend validates: `dfv_completed`
- Publishes to `userSession.discovery` Kafka topic

**Polling:** Shows Discovery running → completed

**Discovery Results Display:**
- JTBD Elements (Job, Outcome, Pain) - array of 3-5 items
- Interview Plan:
  - Target Segment
  - Interview Questions (4-6 questions)
  - Hypothesis to Validate

### 7. Completion & Export
**Session Status:** `completed` (terminal state)

**Available Actions:**
- View consolidated report (all three phases)
- Export as Markdown via frontend utility
- Archive session to start fresh

**Archive:** `DELETE /api/v1/sessions/{id}` → `status: "archived"`
- Student can then create new session
- Previous session preserved in history

---

## Mentor Journey

### 1. Login → `/mentor`
### 2. Mentor Dashboard (`GET /mentor/sessions`)
- Filterable paginated list of supervised team sessions
- Columns: Team, Student, Status, TIPSC Score, Ready for DFV, Updated
- Click row → Full session detail

### 3. Session Detail (`GET /mentor/sessions/{id}`)
- Full session with all outputs (TIPSC, DFV, Discovery)
- Read-only view
- Add comments via `POST /sessions/{id}/comments`

### 4. Mentor Teams (`GET /mentor/teams`)
- List supervised teams with member details
- Active session counts per team

---

## Admin Journey

### 1. Login → `/admin`
### 2. Admin Dashboard
- **All Sessions** (`GET /admin/sessions`) - filterable, paginated
- **Audit Logs** (`GET /admin/audit`) - system-wide, filterable
- **Metrics** (`GET /admin/metrics`) - platform health stats

---

## Error & Edge Case Handling

| Scenario | Behavior |
|----------|----------|
| Active session exists | 409 `ACTIVE_SESSION_EXISTS` - must archive first |
| TIPSC fails | Show error, "Retry TIPSC" button calls trigger endpoint again |
| DFV not unlocked | DFV tab disabled, shows "Complete TIPSC first" |
| DFV returns NO-GO | Discovery tab disabled, shows recommendations |
| Network error during polling | Retry with exponential backoff, max 3 retries |
| Token expires mid-flow | Auto-refresh via `/auth/refresh`, retry original request |
| Idempotency key reused | Returns original session (no duplicate) |

---

## Status-to-UI Mapping

| Backend Status | UI Stage Access |
|----------------|-----------------|
| `created` | Creating... |
| `queued` | TIPSC: In Progress |
| `tipsc_running` | TIPSC: In Progress |
| `tipsc_completed` + `ready_for_dfv=false` | TIPSC: Done (show improvements), DFV: Locked |
| `tipsc_completed` + `ready_for_dfv=true` | TIPSC: Done, DFV: Available |
| `dfv_waiting` | DFV: Available (not triggered) |
| `dfv_running` | DFV: In Progress |
| `dfv_completed` + `decision=NO-GO` | DFV: Done (show recommendations), Discovery: Locked |
| `dfv_completed` + `decision=GO` | DFV: Done, Discovery: Available |
| `discovery_waiting` | Discovery: Available |
| `discovery_running` | Discovery: In Progress |
| `discovery_completed` | Discovery: Done, All Complete |
| `completed` | All Done, Export Available |
| `archived` | Archived (read-only) |
| `*_failed` | Show Error + Retry Button |