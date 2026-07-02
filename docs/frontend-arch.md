# Frontend Architectural Specification: CIE End-to-End Venture Evaluator Platform (JavaScript Version)

This document establishes the comprehensive frontend technical layout, state machine transitions, routing rules, and structural data contracts for the CIE-Evaluator UI dashboard. The interface functions as a purely responsive, domain-agnostic layer that handles state changes from the FastAPI/Kafka/MongoDB Atlas worker queue via asynchronous polling.

---

## 1. End-to-End Core Workflow Lifecycle

The frontend guides students through three progressive gates. Downstream gates are strictly locked until upstream tasks reach a successful state in the MongoDB data session.

```
[STAGE 1: IDEATION, ETHICS & TIPSC VETTING]
├── Student submits baseline Problem Statement (PS)
|   Ask the mandatory 6 questions.
├── Intercepted by Validation, Regulatory & Ethics Gates (Legal/Compliance flags)
└── Unlocks TIPSC Scoring Agent (Up to 3 Interactive Follow-up Prompt Loops)
│
▼ (Requires: TIPSC Validation Flag == true)
[STAGE 2:  DFV ANALYSIS]
├── Triggers Parallel AI Sub-agents (Desirability, Feasibility, Viability)
└── Aggregated by Decision Engine -> Outputs Structured 'GO' or 'NO-GO' with Justification
│
▼ (Requires: DFV Execution Status == 'done')
[STAGE 3: CUSTOMER DISCOVERY & JTBD PLANNER]
└── Generates structured interview questions and Jobs-To-Be-Done matrix
```

### 1.1 Stage 1 Granular Pipeline (Pre-DFV Architecture)

Stage 1 is not a single call — it is a sequential sub-pipeline of discrete checkpoints that must each resolve before the student ever reaches TIPSC scoring, let alone Stage 2 (DFV). The frontend must track and visually represent each sub-step independently, since any one of them can halt the pipeline.

```
User
  │
  ▼
Pre-Evaluation
  │
  ▼
Market Validation
  │
  ▼
Regulatory Mapping
  │
  ▼
Ethics Pre-Screen
  │
  ├── If ethics_pass = False
  │       ❌ Pipeline stops
  │
  └── If ethics_pass = True
          ▼
     TIPSC Evaluation
          ▼
     Follow-up Questions (up to 3)
          ▼
     Final TIPSC Score
          ▼
     Ready for DFV?
```

**Sub-step responsibilities:**

| Order | Sub-Step | Purpose | Frontend Responsibility |
| :--- | :--- | :--- | :--- |
| 1 | **Pre-Evaluation** | Initial sanity/structure check on the raw Problem Statement submission. | Renders loading skeleton on submit; blocks further input until a status is returned. |
| 2 | **Market Validation** | Checks the idea against baseline market signal heuristics. | Displays a lightweight status chip (`processing` → `done`/`failed`) in the Stage 1 timeline. |
| 3 | **Regulatory Mapping** | Flags any legal/regulatory constraints relevant to the idea's domain. | Surfaces any `complianceIssues` inline as advisory (non-blocking) notices. |
| 4 | **Ethics Pre-Screen** | Hard gate — determines `ethics_pass`. | If `ethics_pass === false`, renders the Regulatory/Ethics Alert Banner in its error layout and **halts the pipeline entirely**; no further sub-steps execute and the workflow cannot be resumed from this session. |
| 5 | **TIPSC Evaluation** | Scores the idea against Timely / Importance / Profitability / Solvability / Constraints criteria. | Only triggers once `ethics_pass === true`; renders the TIPSC scoring panel. |
| 6 | **Follow-up Questions** | Up to 3 clarification loops to refine ambiguous TIPSC inputs. | Renders the Follow-up Chat Console (see §4.1); increments `followUpCount` per round and re-triggers TIPSC recalculation after each response. |
| 7 | **Final TIPSC Score** | Consolidated TIPSC output once follow-ups are exhausted or resolved early. | Renders the finalized TIPSC summary card. |
| 8 | **Ready for DFV?** | Boolean checkpoint exposed as `tipscOutput.isReadyForDfv`. | Unlocks the `/dashboard#dfv` route and enables navigation into Stage 2 only when this flag is `true`. |

> **Note:** This granular breakdown supersedes the simplified "Ideation → Ethics → TIPSC" summary shown in the high-level Stage 1 block above. The high-level diagram remains valid as an executive summary; this section is the authoritative sequencing contract for implementation.

---

## 2. Route Topology & Access Control Matrix

The platform runs as a Role-Based Access Control (RBAC) single-page workspace to maintain execution state integrity.

| Route Path | Access Clearance | Allowed Actions & UI View-State Manifest |
| :--- | :--- | :--- |
| `/login` | Public Guest | Renders PES SSO Authentication interface; stores JWT inside secure HTTP-only cookies or context headers. |
| `/dashboard` | Student Profile | Core ideation terminal. Houses Stage 1 (TIPSC Entry, Follow-ups, and Compliance warnings). |
| `/dashboard#dfv` | Student Profile | Guarded View. Unlocks only when Stage 1 updates to `done` in the session database. |
| `/dashboard#discovery` | Student Profile | Guarded View. Unlocks only when Stage 2 updates to `done`. |
| `/mentor` | Mentor Profile | Read-only matrix view tracking all student active sessions, audit trails, and feedback logs. |

---

## 3. Global Component Layout Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            Dynamic Top Navigation Bar                        │
│   User: [Student SRN] | Session ID: [UUID] | System State: [Processing...]   │
├──────────────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────┐ ┌─────────────────────────────────────────────────┐ │
│ │                      │ │           Active Workspace Viewport             │ │
│ │  [Tab 1] TIPSC Guard │ │                                                 │ │
│ │  [Tab 2] DFV Deep    │ │  • Renders Component Skeletons (Processing)     │ │
│ │  [Tab 3] JTBD Plan   │ │  • Displays Context Alerts     (Error/Issues)   │ │
│ │                      │ │  • Renders Fully Loaded Cards  (Done/Success)   │ │
│ └──────────────────────┘ └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. UI Section Functional Specifications

### 4.1 Stage 1: Preeval, Ethics, and TIPSC Interface

Implements the granular pipeline defined in §1.1 (Pre-Evaluation → Market Validation → Regulatory Mapping → Ethics Pre-Screen → TIPSC Evaluation → Follow-ups → Final TIPSC Score → Ready for DFV).

* **Sub-Step Progress Timeline:** A vertical stepper reflecting the current position within the §1.1 pipeline (Pre-Evaluation, Market Validation, Regulatory Mapping, Ethics Pre-Screen, TIPSC Evaluation), each rendered with its own Loading/Success/Error state.
* **Regulatory/Ethics Alert Banner:** Intercepts compliance data configurations. If the `complianceFlag` (i.e., `ethics_pass`) returns `false`, it shifts to an error layout, displays ethical violation highlights (legal or safety blocks), and completely disables the project workflow — matching the hard-stop behavior at the Ethics Pre-Screen checkpoint in §1.1.
* **Follow-up Chat Console:** A micro-terminal component designed to appear dynamically if the TIPSC task returns a requirement for further clarification. It limits interactions strictly to **3 follow-up cycles**, recalculating TIPSC parameters incrementally after each student response.
* **DFV Readiness Indicator:** Reflects `tipscOutput.isReadyForDfv`; only when `true` does the UI enable navigation to `/dashboard#dfv`.

### 4.2 Stage 2: Deep Parallel DFV Interface

* **Worker Execution Status Container:** Tracks parallel sub-agent workflows. Visually indicates independent progression states for the Desirability, Feasibility, and Viability agents.
* **Decision Gate Board:** Displays the ultimate aggregated project verdict.
  * `GO`: Renders an optimistic emerald layout providing strategic incubation validation.
  * `NO-GO`: Renders a deep crimson alert layout highlighting the primary structural fatal flaw across the three pillars.

### 4.3 Stage 3: Customer Discovery & JTBD Planner

* **Jobs-To-Be-Done Matrix Display:** Renders clear cards tracking student core customer functional, social, and emotional motivations.
* **Dynamic Interview Guide:** Provides an actionable, copyable list of targeted field questions sorted by user personas, generated directly from the successful backend execution context.

---

## 5. State Management & Asynchronous Polling Engine

The client uses an automated polling controller to handle tracking lifecycle updates from Kafka topics and MongoDB Atlas tables without requiring page reloads.

### 5.1 Main Unified JavaScript Object Blueprint (JSDoc Documentation)

```javascript
/**
 * @typedef {('queued'|'processing'|'done'|'failed')} TaskWorkerStatus
 */

/**
 * @typedef {Object} VentureSession
 * @property {string} sessionId - Unique identifier for the user session
 * @property {string} studentSrn - Student registration credentials identifier
 * @property {('COMPLIANCE'|'TIPSC'|'DFV'|'JTBD')} currentStep - Active step in workflow sequence
 * @property {TaskWorkerStatus} globalStatus - Async execution worker track status
 * @property {boolean} complianceFlag - Legal and ethics validation approval checkpoint status
 * @property {string[]} complianceIssues - Array of targeted policy infraction descriptions
 * @property {number} followUpCount - Counter tracking current interaction loop index (Max: 3)
 * @property {Object|null} tipscOutput - Vetting parameter summary data blocks
 * @property {string} tipscOutput.timely - Rationale behind macro environmental trend market timing
 * @property {string} tipscOutput.importance - Severity justification indicator
 * @property {string} tipscOutput.profitability - Sustainable business model pricing configuration
 * @property {string} tipscOutput.solvability - Basic execution capability metric
 * @property {string} tipscOutput.constraints - Operations boundaries checklist context
 * @property {boolean} tipscOutput.isReadyForDfv - Flag unlocking Phase 2 sub-agents
 * @property {Object|null} dfvOutput - Deep parallel agent analysis metrics
 * @property {Object} dfvOutput.refinedIdea - Sanitized version of raw proposal parameters
 * @property {string} dfvOutput.refinedIdea.segment - Target customer audience focus definition
 * @property {string} dfvOutput.refinedIdea.problem - Pain point mapping parameter
 * @property {string} dfvOutput.refinedIdea.consequence - Negative fallout tracking argument
 * @property {string} dfvOutput.refinedIdea.solution - Core product fix value prop
 * @property {Object} dfvOutput.hypotheses - Core assumptions framed as testable metrics
 * @property {string} dfvOutput.hypotheses.desirability - Target behavior confirmation assumption
 * @property {string} dfvOutput.hypotheses.feasibility - Engineering deployment method assumption
 * @property {string} dfvOutput.hypotheses.viability - Economic engine scaling capability assumption
 * @property {Object} dfvOutput.decision - Final project gate validation status object
 * @property {('GO'|'NO-GO')} dfvOutput.decision.status - Ultimate milestone operational clearance verdict
 * @property {string} dfvOutput.decision.justification - Data-backed analytical reason for target status
 * @property {Object|null} jtbdOutput - Phase 3 validation output blocks
 * @property {string[]} jtbdOutput.targetPersonas - Target customer profiles
 * @property {string[]} jtbdOutput.interviewQuestions - Persona field research validation interview guides
 * @property {string[]} jtbdOutput.coreJobs - Core Jobs-To-Be-Done targets
 * @property {string|null} errorContext - Dynamic backend server stack trace capture block
 */

// Initial Template Representation of the Session State Object
const initialVentureSessionState = {
  sessionId: "",
  studentSrn: "",
  currentStep: "COMPLIANCE",
  globalStatus: "queued",
  complianceFlag: true,
  complianceIssues: [],
  followUpCount: 0,
  tipscOutput: null,
  dfvOutput: null,
  jtbdOutput: null,
  errorContext: null
};
```

### 5.2 Polling Lifecycle Synchronization Hook

* **Triggers:** Automatically initializes on user form submissions (`POST /userSession`).
* **Cadence Engine:** Issues non-blocking asynchronous `fetch` or `axios` operations targeting the `/api/v1/session/{id}` endpoint exactly every 5000ms (5 seconds).
* **Button Idempotency Lock:** Automatically locks all interactive input fields and submit actions on the dashboard UI while `globalStatus === 'processing'` to block duplicate request injections.
* **Termination Criteria:** Clears and breaks the polling thread interval using `clearInterval()` only when the session state shifts to `done` or `failed`.

---

## 6. Defensive Bounds Handling & Fault Mitigation

* **Dynamic Text Wrapping Layouts:** Because student ideas represent unpredictable domains, all layout components must reject hardcoded pixel heights (`h-auto` and `w-full` exclusively). Use Tailwind properties `break-words` and `whitespace-normal` to protect layouts against long string inputs.
* **Malformed JSON Sanitizer Blocks:** Local LLM instances can sometimes return erratic markdown syntax around response text blocks. The frontend client data-handler must execute programmatic string extractions (e.g., using `indexOf('{')` and `lastIndexOf('}')`) to isolate pure JSON fields before parsing.
* **Graceful Session Restorations:** Frontend applications cache user inputs inside `localStorage` buffers. If an internet drop occurs mid-pipeline, the user retains their exact text layouts upon reconnecting without data loss.
