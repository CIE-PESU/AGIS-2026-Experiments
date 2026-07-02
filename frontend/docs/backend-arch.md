<<<<<<< Updated upstream

# Backend Architecture

======

# AGIS Entrepreneurship Coach Platform

# Backend Architecture Document

**Version:** 2.0
**Status:** For Approval Before Implementation
**Prepared By:** Principal Backend Architect
**Date:** June 2026

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Backend Folder Structure](#3-backend-folder-structure)
4. [Backend Responsibilities](#4-backend-responsibilities)
5. [Session Lifecycle](#5-session-lifecycle)
6. [State Machine](#6-state-machine)
7. [Authentication Architecture](#7-authentication-architecture)
8. [MongoDB Design](#8-mongodb-design)
9. [Repository Layer](#9-repository-layer)
10. [Service Layer](#10-service-layer)
11. [Kafka Architecture](#11-kafka-architecture)
12. [Worker Communication](#12-worker-communication)
13. [API Design Philosophy](#13-api-design-philosophy)
14. [Error Handling](#14-error-handling)
15. [Logging](#15-logging)
16. [Security](#16-security)
17. [Performance](#17-performance)
18. [Scalability](#18-scalability)
19. [Edge Cases](#19-edge-cases)
20. [Future Improvements](#20-future-improvements)

---

# 1. System Overview

## 1.1 Purpose of the Backend

The backend is the **single source of truth** and the **central integrity enforcer** of the AGIS platform. It does not perform AI computation. It does not consume Kafka messages. It does not render UI. It exists to coordinate all other components and ensure that no action is taken without proper authorization, validation, and traceability.

Every piece of data, every state change, every user action, and every AI output is either owned or validated by the backend before any downstream effect occurs.

## 1.2 What the Backend Owns

| Concern                                                   | Owner   |
| --------------------------------------------------------- | ------- |
| Authentication and JWT issuance                           | Backend |
| Role-Based Access Control enforcement                     | Backend |
| Session creation and lifecycle                            | Backend |
| State machine enforcement                                 | Backend |
| MongoDB reads and writes (API path)                       | Backend |
| Kafka event publishing                                    | Backend |
| Audit log generation                                      | Backend |
| Mentor view APIs                                          | Backend |
| Input validation                                          | Backend |
| OpenAPI documentation                                     | Backend |
| Worker result validation (if using internal API approach) | Backend |

## 1.3 What the Backend Must Never Do

| Concern                                         | Why It Must Not Be Backend's Responsibility                            |
| ----------------------------------------------- | ---------------------------------------------------------------------- |
| Execute CrewAI agents                           | Agents are long-running, compute-heavy, and would block the event loop |
| Consume Kafka messages                          | Consumption is the Worker team's domain                                |
| Render or decide UI content                     | Frontend owns presentation logic                                       |
| Call external AI APIs directly                  | All AI is encapsulated in agents, run only by workers                  |
| Make business decisions about AI output quality | Workers validate CrewAI output before writing to DB                    |

## 1.4 System Boundaries

```
┌───────────────────────────────────────────────────────────────────┐
│                         BROWSER / CLIENT                          │
│                        React Frontend                             │
└───────────────────────┬───────────────────────────────────────────┘
                        │  HTTPS REST (JWT Bearer)
                        ▼
┌───────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                              │
│  Auth │ Sessions │ State Machine │ Kafka Producer │ Audit Logs   │
│  RBAC │ Mentor APIs │ Validation │ OpenAPI │ Idempotency         │
└───────┬───────────────────────┬──────────────────────────────────┘
        │                       │
        ▼                       ▼
┌──────────────┐     ┌─────────────────────────────────────────────┐
│ MongoDB Atlas│     │            Apache Kafka                     │
│ (Persistence)│     │  userSession.tipsc / .dfv / .discovery      │
│              │     │  userSession.notifications                  │
└──────────────┘     └──────────────────────┬────────────────────-─┘
                                            │
                                            ▼
                               ┌────────────────────────┐
                               │    Worker Services      │
                               │ (Worker Team's Domain)  │
                               └────────────┬───────────┘
                                            │
                                            ▼
                               ┌────────────────────────┐
                               │    CrewAI Agents        │
                               │  TIPSC / DFV / Discovery│
                               └────────────┬───────────┘
                                            │
                                            ▼
                               ┌────────────────────────┐
                               │   MongoDB Atlas         │
                               │  (Worker writes output) │
                               └────────────────────────┘
```

**Boundary Rules:**

- Frontend communicates ONLY with the backend via HTTPS REST.
- Backend communicates ONLY with MongoDB (reads/writes), Kafka (publish only), and PES Auth API.
- Workers communicate ONLY with Kafka (consume), CrewAI agents (invoke), and MongoDB (write output).
- Workers NEVER receive instructions from the frontend.
- The frontend NEVER queries MongoDB directly.
- CrewAI agents NEVER have network visibility outside the worker sandbox.

---

# 2. High-Level Architecture

## 2.1 Complete Request Flow — Session Creation

```
Student (Browser)
        │
        │  POST /api/v1/sessions
        │  { problem_statement, idea }
        │  Authorization: Bearer <JWT>
        ▼
FastAPI Backend
        │
        ├── 1. JWT Middleware validates token
        ├── 2. Extract user_id, role, team_id from JWT
        ├── 3. RBAC check: only students can create sessions
        ├── 4. Input validation (Pydantic schema)
        ├── 5. Check idempotency key (no duplicate session)
        ├── 6. Check: student already has active session? → 409
        ├── 7. Write session to MongoDB {status: CREATED}
        ├── 8. Write audit log: SESSION_CREATED
        ├── 9. Publish Kafka event to userSession.tipsc
        ├── 10. Update session status to QUEUED in MongoDB
        ├── 11. Write audit log: TIPSC_TRIGGERED
        └── 12. Return { session_id, status: "queued" }
        │
        ▼
React Frontend
        │
        │  GET /api/v1/sessions/{id}  (every 5 seconds)
        ▼
FastAPI Backend
        │
        ├── JWT + RBAC check
        ├── Fetch session from MongoDB
        └── Return full session document with current status
```

## 2.2 Worker Completion Flow

```
Kafka (userSession.tipsc)
        │
        ▼
Worker Service (Worker Team)
        │
        ├── Consume message
        ├── Update MongoDB: status → TIPSC_RUNNING
        ├── Invoke TIPSC CrewAI Agent
        ├── Receive TIPSC output
        ├── Validate output schema
        ├── Write output to MongoDB sessions.tipsc
        ├── Update MongoDB: status → TIPSC_COMPLETED
        ├── Publish to userSession.notifications
        └── (Optional) Call POST /api/v1/internal/sessions/{id}/status
                        with { status, output, worker_id, correlation_id }
```

## 2.3 Frontend Polling Flow

```
React Frontend
        │
        │  GET /api/v1/sessions/{id}  every 5 seconds
        ▼
FastAPI Backend
        │
        ├── Validate JWT
        ├── Check RBAC: can this user view this session?
        ├── Query MongoDB (indexed on _id)
        └── Return: { status, tipsc: {}, dfv: {}, discovery: {} }
        │
        ▼
React Frontend
        │
        ├── If status == TIPSC_COMPLETED → show TIPSC output, unlock DFV tab
        ├── If status == DFV_COMPLETED → show DFV output, unlock Discovery tab
        ├── If status == COMPLETED → show all outputs
        └── If status == FAILED → show error, offer retry
```

---

# 3. Backend Folder Structure

```
backend/
└── app/
    │
    ├── api/                        # HTTP route handlers only — no business logic here
    │   ├── v1/                     # Version namespace
    │   │   ├── __init__.py
    │   │   ├── auth.py             # /auth/login, /auth/logout, /auth/me
    │   │   ├── sessions.py         # /sessions CRUD + trigger endpoints
    │   │   ├── flows.py            # /sessions/{id}/trigger/{flow}
    │   │   ├── history.py          # /sessions/{id}/history
    │   │   ├── comments.py         # /sessions/{id}/comments
    │   │   ├── mentor.py           # /mentor/* endpoints
    │   │   ├── admin.py            # /metrics, /audit, /logs
    │   │   └── health.py           # /health, /ready, /live
    │   └── internal/               # Backend-only endpoints (worker callbacks)
    │       └── worker_updates.py
    │
    ├── schemas/                    # Pydantic request/response shapes (API contract)
    │   ├── auth.py
    │   ├── session.py
    │   ├── flow.py
    │   ├── comment.py
    │   ├── mentor.py
    │   └── common.py              # Pagination, BaseResponse, ErrorResponse
    │
    ├── models/                    # MongoDB document models (Beanie ODM)
    │   ├── user.py
    │   ├── team.py
    │   ├── session.py
    │   ├── audit.py
    │   └── comment.py
    │
    ├── repositories/              # All MongoDB interaction goes here — nothing else queries DB
    │   ├── base.py                # Generic CRUD base
    │   ├── session_repo.py
    │   ├── user_repo.py
    │   ├── audit_repo.py
    │   └── comment_repo.py
    │
    ├── services/                  # Business logic — routes call services, services call repos
    │   ├── auth_service.py        # PES Auth integration, JWT issuance
    │   ├── session_service.py     # Session lifecycle, state transitions
    │   ├── flow_service.py        # Flow trigger logic, state validation
    │   ├── audit_service.py       # Audit log writing
    │   ├── mentor_service.py      # Mentor-specific business rules
    │   └── comment_service.py
    │
    ├── state_machine/             # Finite state machine — centralized, testable
    │   ├── states.py              # Enum of all states
    │   ├── transitions.py         # Allowed and forbidden transitions
    │   └── validator.py           # Validates transition before execution
    │
    ├── kafka/                     # Kafka producer only — no consumers here
    │   ├── producer.py            # aiokafka producer singleton
    │   ├── topics.py              # Topic name constants
    │   └── payloads.py            # Typed Pydantic payload schemas for events
    │
    ├── auth/                      # Authentication and authorization logic
    │   ├── jwt.py                 # Token creation, parsing, validation
    │   ├── pes_client.py          # HTTP client for PES Auth API
    │   └── dependencies.py        # FastAPI Depends() for current_user, require_role
    │
    ├── middleware/                # Request lifecycle middleware
    │   ├── request_id.py          # Inject X-Request-ID into every request
    │   ├── correlation.py         # Propagate correlation IDs across layers
    │   ├── logging.py             # Structured request/response logging
    │   └── rate_limit.py          # Per-user rate limiting
    │
    ├── database/                  # Database connection and config
    │   ├── mongodb.py             # Motor/Beanie init, connection lifecycle
    │   └── indexes.py             # Index definitions — created on startup
    │
    ├── exceptions/                # Custom exception hierarchy
    │   ├── base.py
    │   ├── auth.py
    │   ├── session.py
    │   ├── kafka.py
    │   └── handlers.py            # Global FastAPI exception handlers
    │
    ├── events/                    # Application lifecycle events
    │   ├── startup.py             # DB connect, Kafka producer init, index creation
    │   └── shutdown.py            # Graceful cleanup
    │
    ├── dependencies/              # FastAPI dependency injection
    │   ├── auth.py                # get_current_user, require_role
    │   ├── pagination.py
    │   └── session.py             # get_session_or_404
    │
    ├── logging/                   # Logging configuration
    │   ├── config.py              # structlog or logging setup
    │   └── masking.py             # PII/secret masking
    │
    ├── utils/                     # Pure utility functions
    │   ├── idempotency.py         # Idempotency key generation and checking
    │   ├── pagination.py
    │   └── validators.py
    │
    ├── core/                      # System-wide constants and config
    │   ├── config.py              # Pydantic Settings — reads from env
    │   └── constants.py
    │
    └── main.py                    # FastAPI app factory, router registration, middleware mounting
```

**Why this structure matters:**

Each directory has a single responsibility. Routes never touch MongoDB. Services never import Kafka directly — they call the Kafka service layer. Repositories are the only layer that knows about MongoDB. The state machine is isolated and unit-testable without needing a running database. This separation ensures any individual layer can be swapped, tested, or replaced without cascading changes.

---

# 4. Backend Responsibilities

## 4.1 Authentication

The backend is the **gatekeeper**. It validates JWT tokens on every protected request. It does not store passwords. It delegates credential verification to the PES Auth API and then issues its own short-lived JWT.

- Token issuance is the backend's responsibility.
- Token revocation is handled via short expiry (15 minutes) and refresh token rotation.
- PES Auth API unavailability must return `503`, not `500`.

## 4.2 Authorization (RBAC)

Authorization is enforced at the dependency layer, not inside route handlers. Every protected route declares which roles are permitted. This means authorization cannot accidentally be skipped. The state machine is the second line of defense — it prevents out-of-order actions even from authorized users.

## 4.3 Validation

All incoming data is validated at the Pydantic schema layer before any service logic executes. Validation is the first thing that happens after authentication — before any database or Kafka interaction. The backend enforces:

- Field presence and type
- String length limits
- Enum membership (flow names, roles)
- Structural correctness

## 4.4 Session Lifecycle

The backend owns session creation, state transitions, and final status. It does not execute flows. It publishes the intent to execute a flow to Kafka, then trusts workers to report completion through their chosen communication path (direct MongoDB write or internal API callback).

## 4.5 Database

The backend is the primary writer for the API-initiated path. Workers write independently during execution. The backend defines all index strategy, collection schema, and soft-delete conventions.

## 4.6 Kafka

The backend produces events only. A failed Kafka publish must roll back the session state and return an error to the user. The frontend must never be told "queued" if the event was never published.

## 4.7 Audit Logging

Every significant system event generates an immutable audit log entry. Audit failures do not block the main operation, but they are retried asynchronously. The audit log is the source of truth for compliance and debugging.

## 4.8 Error Handling

Errors are structured, typed, and carry enough information to act on. Internal errors are never exposed to the client. All exception handlers are centralized in `exceptions/handlers.py`.

## 4.9 Worker Coordination

The backend validates all worker-produced updates before accepting them. Workers must send a `correlation_id` that matches what was published. A worker attempting to update a session that is in a terminal state (`COMPLETED`, `FAILED`) is rejected.

## 4.10 Mentor APIs

Mentors have read-only access to sessions. They can add comments. The mentor API must enforce that mentors can only see sessions that belong to teams they supervise, not all sessions in the system.

## 4.11 Versioning

All routes are versioned under `/api/v1`. Future breaking changes introduce `/api/v2`. Non-breaking changes (new optional fields, new non-destructive endpoints) are made in place.

---

# 5. Session Lifecycle

## 5.1 Complete Lifecycle Diagram

```
           Student POSTs /sessions
                    │
                    ▼
            ┌─────────────┐
            │   CREATED   │ ← Session written to DB
            └──────┬──────┘
                   │ Kafka publish succeeds
                   ▼
            ┌─────────────┐
            │   QUEUED    │ ← Kafka event published
            └──────┬──────┘
                   │ Worker picks up message
                   ▼
         ┌──────────────────┐
         │  TIPSC_RUNNING   │ ← Worker updates DB
         └────────┬─────────┘
                  │
         ┌────────┴─────────┐
         │                  │
         ▼                  ▼
  ┌─────────────┐    ┌────────────┐
  │TIPSC_FAILED │    │TIPSC_DONE  │
  └──────┬──────┘    └──────┬─────┘
         │                  │
         ▼                  │ Student reviews TIPSC output
   ┌──────────┐             │
   │  RETRY   │             ▼
   └──────────┘    ┌──────────────────┐
                   │  DFV_WAITING     │ ← Student must trigger DFV manually
                   └──────┬───────────┘
                          │ Student POSTs trigger/dfv
                          ▼
                   ┌──────────────────┐
                   │   DFV_RUNNING    │
                   └──────┬───────────┘
                          │
                 ┌────────┴────────┐
                 │                 │
                 ▼                 ▼
          ┌───────────┐    ┌─────────────┐
          │ DFV_FAILED│    │ DFV_DONE    │
          └───────────┘    └──────┬──────┘
                                  │ Student triggers discovery
                                  ▼
                         ┌─────────────────────┐
                         │  DISCOVERY_WAITING  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  DISCOVERY_RUNNING  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                              ┌──────────┐
                              │COMPLETED │ ← Terminal state
                              └──────────┘
```

## 5.2 Cancellation and Archive

A student may archive a session at any point (except while a flow is RUNNING). Archiving sets `status = ARCHIVED` and `archived_at = now()`. Archived sessions are excluded from the active session query but are retrievable by history APIs.

## 5.3 Restart Behavior

A student may start a new session only after archiving the current one. The previous session's scores are written to the DB (preserved) and the student begins fresh. The system does not delete old sessions.

---

# 6. State Machine

## 6.1 Allowed Transitions

| From State        | Trigger                      | To State          | Who Can Trigger              |
| ----------------- | ---------------------------- | ----------------- | ---------------------------- |
| —                | Student creates session      | CREATED           | Student                      |
| CREATED           | Kafka publish succeeds       | QUEUED            | Backend (automatic)          |
| QUEUED            | Worker picks up              | TIPSC_RUNNING     | Worker                       |
| TIPSC_RUNNING     | Worker succeeds              | TIPSC_COMPLETED   | Worker                       |
| TIPSC_RUNNING     | Worker fails                 | TIPSC_FAILED      | Worker                       |
| TIPSC_FAILED      | Retry threshold not exceeded | QUEUED            | Backend (retry)              |
| TIPSC_COMPLETED   | Student triggers DFV         | DFV_WAITING       | Backend (on student request) |
| DFV_WAITING       | Worker picks up              | DFV_RUNNING       | Worker                       |
| DFV_RUNNING       | Worker succeeds              | DFV_COMPLETED     | Worker                       |
| DFV_RUNNING       | Worker fails                 | DFV_FAILED        | Worker                       |
| DFV_COMPLETED     | Student triggers discovery   | DISCOVERY_WAITING | Backend                      |
| DISCOVERY_WAITING | Worker picks up              | DISCOVERY_RUNNING | Worker                       |
| DISCOVERY_RUNNING | Worker succeeds              | COMPLETED         | Worker                       |
| DISCOVERY_RUNNING | Worker fails                 | DISCOVERY_FAILED  | Worker                       |
| ANY (non-running) | Student archives             | ARCHIVED          | Student                      |

## 6.2 Forbidden Transitions

| Attempted Transition             | Why Forbidden                       |
| -------------------------------- | ----------------------------------- |
| TIPSC_RUNNING → DFV_RUNNING     | Cannot run two flows simultaneously |
| TIPSC_COMPLETED → TIPSC_RUNNING | Cannot re-run a completed flow      |
| COMPLETED → any flow state      | Session is terminal                 |
| ARCHIVED → any active state     | Archived sessions are immutable     |
| QUEUED → COMPLETED              | Cannot skip states                  |
| DFV_WAITING → TIPSC_RUNNING     | Cannot go backwards                 |

## 6.3 Enforcement

State validation is performed in the `state_machine/validator.py` module, called from `flow_service.py` before any Kafka publish or DB write. If the transition is forbidden, the service raises a `InvalidStateTransitionError` which maps to `409 Conflict`.

**Rationale:** Centralizing state machine logic prevents the situation where route A allows a transition that route B blocks. All state logic lives in one testable module with no database or Kafka dependency.

---

# 7. Authentication Architecture

## 7.1 Login Flow

```
Student provides SRN + password
        │
        ▼
POST /api/v1/auth/login
        │
        ▼
Backend → PES Auth API (HTTP POST)
        │
        ├── PES returns: VALID → extract name, srn, role
        ├── PES returns: INVALID → 401 Unauthorized
        └── PES timeout (>5s) → 503 Service Unavailable
        │
        ▼ (on VALID)
Backend creates/updates user document in MongoDB
        │
        ▼
Backend generates JWT:
{
  "sub": "user_id",
  "role": "student",
  "team_id": "team_xyz",
  "srn": "PES2UG22CS001",
  "iat": ...,
  "exp": ... (15 minutes)
}
        │
        ▼
Backend generates refresh_token (opaque, 7 days, stored in DB)
        │
        ▼
Return { access_token, refresh_token, role }
```

## 7.2 Token Refresh Flow

```
Access token expires (401 received by frontend)
        │
        ▼
Frontend POSTs /auth/refresh with refresh_token
        │
        ▼
Backend validates refresh_token against DB
        │
        ├── Valid and not expired → issue new access_token + rotate refresh_token
        └── Invalid or expired → 401, force re-login
```

## 7.3 JWT Middleware

Every protected route uses a FastAPI `Depends(get_current_user)` dependency that:

1. Extracts `Authorization: Bearer <token>` header.
2. Verifies signature with the backend's secret key.
3. Checks `exp` claim.
4. Extracts `sub`, `role`, `team_id`.
5. Returns a typed `CurrentUser` object.

Routes that need RBAC additionally use `Depends(require_role(["student"]))`.

## 7.4 Security Notes

- JWT secret is environment-variable-only, never hardcoded.
- Access tokens are short-lived (15 minutes). Even if intercepted, the window is narrow.
- Refresh tokens are opaque random strings stored hashed in MongoDB. If compromised, they can be revoked server-side.
- Logout endpoint invalidates the refresh token in MongoDB. Access tokens are stateless and expire naturally.

---

# 8. MongoDB Design

## 8.1 Collections

| Collection          | Purpose                                                |
| ------------------- | ------------------------------------------------------ |
| `users`           | One document per authenticated user                    |
| `teams`           | One document per student team                          |
| `sessions`        | One document per student session (the core collection) |
| `audit_logs`      | Immutable append-only event log                        |
| `mentor_comments` | Comments added by mentors                              |
| `refresh_tokens`  | Opaque refresh tokens with expiry (TTL collection)     |

## 8.2 Embedding vs Referencing Strategy

**Embed when:** The data is always read together, is bounded in size, and has no independent identity outside the parent.

**Reference when** The data has its own lifecycle, can grow unboundedly, or is queried independently.

| Data                        | Strategy                      | Rationale                                                    |
| --------------------------- | ----------------------------- | ------------------------------------------------------------ |
| TIPSC output in session     | **Embed**               | Always read with session, bounded, no independent queries    |
| DFV output in session       | **Embed**               | Same as above                                                |
| Discovery output in session | **Embed**               | Same as above                                                |
| Audit logs                  | **Separate collection** | Append-only, large volume, queried independently by timeline |
| Mentor comments             | **Separate collection** | Can be deleted independently, queried independently          |
| User in session             | **Reference (user_id)** | User data is stable reference data                           |
| Team in session             | **Reference (team_id)** | Team has its own lifecycle                                   |

## 8.3 Index Strategy

| Collection      | Index                       | Type            | Reason                                    |
| --------------- | --------------------------- | --------------- | ----------------------------------------- |
| sessions        | `student_id`              | Single          | Fetch all sessions by student             |
| sessions        | `team_id`                 | Single          | Mentor fetches team sessions              |
| sessions        | `status`                  | Single          | Filter by state (admin, monitoring)       |
| sessions        | `(student_id, status)`    | Compound        | Active session lookup (most common query) |
| sessions        | `created_at`              | Single (desc)   | Timeline ordering                         |
| audit_logs      | `session_id`              | Single          | Fetch session history                     |
| audit_logs      | `timestamp`               | Single          | Chronological ordering                    |
| audit_logs      | `(session_id, timestamp)` | Compound        | Timeline query for a session              |
| mentor_comments | `session_id`              | Single          | Fetch comments for a session              |
| refresh_tokens  | `token_hash`              | Single + Unique | Fast lookup during refresh                |
| refresh_tokens  | `expires_at`              | TTL             | Auto-delete expired tokens                |

## 8.4 Soft Delete Strategy

Sessions are never hard-deleted. Setting `status = ARCHIVED` and `archived_at = timestamp` constitutes archival. All active queries filter `status != ARCHIVED`. This preserves history and allows potential recovery.

## 8.5 Optimistic Concurrency

Worker updates and API updates may collide. Use MongoDB's `update_one` with a version field check:

```
Find session WHERE _id == X AND version == N
Update SET status = NEW_STATUS, version = N+1
```

If the update matches 0 documents, the version has changed — reject the update and retry or raise a conflict error.

## 8.6 Scaling Strategy

- MongoDB Atlas with M30+ cluster for production.
- Read replicas for GET-heavy endpoints (mentor dashboard, polling).
- Shard key on `team_id` if collection grows beyond 100GB.
- Atlas Search for future full-text search on problem statements.

---

# 9. Repository Layer

## 9.1 Why a Repository Layer Exists

Without repositories, MongoDB query logic bleeds into services, which bleeds into routes. This creates three problems:

1. **Testability:** You cannot unit-test service logic without spinning up a MongoDB instance.
2. **Duplication:** The same query appears in multiple routes with minor variations.
3. **Coupling:** Switching from Motor to Beanie (or any future change) requires touching every service.

Repositories are the **only layer that knows MongoDB exists**. Everything above repositories treats data access as function calls with typed return values.

## 9.2 Repository Contract

Each repository exposes typed async methods:

```
SessionRepository:
  + create(session: SessionCreate) → Session
  + find_by_id(session_id: str) → Session | None
  + find_by_student(student_id: str) → list[Session]
  + update_status(session_id: str, status: SessionStatus, version: int) → bool
  + update_flow_output(session_id: str, flow: str, output: dict) → bool
  + archive(session_id: str) → bool
```

Services call repositories. Routes call services. Routes never call repositories.

## 9.3 Idempotency in Repositories

The `create` method accepts an optional `idempotency_key`. Before inserting, it checks whether a document with the same key exists. If it does, it returns the existing document. If not, it inserts. This is atomic via MongoDB's `findOneAndUpdate` with `upsert=True`.

---

# 10. Service Layer

## 10.1 Purpose

Services contain all business logic that is not HTTP-specific and not database-specific. They orchestrate repositories, state machine validation, Kafka publishing, and audit logging into coherent operations.

## 10.2 Service Responsibilities

| Service            | Responsibilities                                                           |
| ------------------ | -------------------------------------------------------------------------- |
| `AuthService`    | Call PES API, generate JWT, handle refresh, validate token                 |
| `SessionService` | Create session, fetch session, archive session, validate ownership         |
| `FlowService`    | Validate state transition, publish Kafka event, update status              |
| `AuditService`   | Write audit log entries (fire-and-forget with retry)                       |
| `MentorService`  | Fetch supervised teams, filter sessions by team, enforce mentor boundaries |
| `CommentService` | Create comment, validate comment length, enforce mentor-only creation      |

## 10.3 Transaction-Like Behavior

MongoDB multi-document transactions are available but expensive. The preferred pattern for operations that touch multiple collections is:

1. Write the primary document first.
2. Write the audit log second (can retry independently).
3. Publish Kafka event last (only after DB write confirms).

If Kafka publish fails, roll back the session status to its previous state in MongoDB. This ensures the user is never told "queued" when no event exists in Kafka.

---

# 11. Kafka Architecture

## 11.1 Topic Design

| Topic                         | Producer | Consumer            | Purpose                    |
| ----------------------------- | -------- | ------------------- | -------------------------- |
| `userSession.tipsc`         | Backend  | TIPSC Worker        | Trigger TIPSC evaluation   |
| `userSession.dfv`           | Backend  | DFV Worker          | Trigger DFV evaluation     |
| `userSession.discovery`     | Backend  | Discovery Worker    | Trigger discovery planner  |
| `userSession.notifications` | Workers  | Notification Worker | Completion/failure signals |

**Partition Strategy:** Partition by `team_id` or `session_id` to ensure ordering within a session's events. This prevents a completion event from being processed before a start event.

## 11.2 Message Payload Schema

All Kafka messages use this envelope:

```json
{
  "event_id": "uuid-v4",
  "correlation_id": "uuid-v4",
  "session_id": "string",
  "team_id": "string",
  "student_id": "string",
  "flow": "tipsc | dfv | discovery",
  "timestamp": "ISO8601",
  "schema_version": "1.0",
  "payload": {
    // flow-specific input data
  }
}
```

`event_id` is unique per publish. Workers use it for idempotency (deduplicate by `event_id`).
`correlation_id` ties the entire request chain together (API call → Kafka event → worker execution → DB write).

## 11.3 Delivery Guarantees

| Property    | Choice                                           | Rationale                                                     |
| ----------- | ------------------------------------------------ | ------------------------------------------------------------- |
| Delivery    | At-least-once                                    | Exactly-once requires distributed transactions; overkill here |
| Idempotency | Worker deduplication by`event_id`              | Compensates for at-least-once delivery                        |
| Ordering    | Per-partition ordering (partition by session_id) | Events for the same session always arrive in order            |
| Retention   | 7 days                                           | Allows worker replay after outages                            |

## 11.4 Duplicate Publish Prevention

Before publishing, the backend:

1. Checks session status — if already `QUEUED` or `RUNNING`, rejects with `409`.
2. Uses an idempotency key (`session_id + flow + attempt_number`) to prevent double-publish from retry logic.
3. Wraps the DB status update and Kafka publish in a try/except. If Kafka fails, rolls back DB status.

## 11.5 Dead Letter Queue

Each topic has a companion DLQ:

| Topic                     | DLQ                           |
| ------------------------- | ----------------------------- |
| `userSession.tipsc`     | `userSession.tipsc.dlq`     |
| `userSession.dfv`       | `userSession.dfv.dlq`       |
| `userSession.discovery` | `userSession.discovery.dlq` |

Workers send unprocessable messages to the DLQ after 3 failed attempts. The backend can query DLQ depth as part of the admin dashboard. Ops team manually inspects DLQ messages.

---

# 12. Worker Communication

## 12.1 Two Architecture Options

### Option A: Workers Write Directly to MongoDB

```
Worker → MongoDB (direct write)
```

Workers update session status and output directly in MongoDB. The backend reads the updated document on the next polling request.

**Pros:**

- Simpler — one fewer network hop
- Lower latency
- No backend availability dependency for worker completion

**Cons:**

- Workers must have MongoDB credentials (wider blast radius if compromised)
- Workers must know the DB schema intimately
- Schema changes require updating both backend and workers
- No centralized validation of worker output
- No audit log automatically generated by the backend for worker events

### Option B: Workers Call Internal Backend API

```
Worker → POST /api/v1/internal/sessions/{id}/status → Backend → MongoDB
```

**Pros:**

- Backend validates all worker output before it touches the DB
- Schema changes are isolated to backend
- Workers don't need MongoDB credentials
- Audit logs are generated by backend for worker completions
- Workers are fully decoupled from persistence layer

**Cons:**

- One additional network hop
- Backend availability is required for worker completion (minor — backend is highly available)
- Internal API must be secured (internal network + shared secret / service token)

## 12.2 Recommendation

**Use a hybrid approach:**

- Workers write **execution status** (RUNNING, COMPLETED, FAILED) directly to MongoDB using a **separate service account** with write-only access to the `sessions.status` field only.
- Workers POST **output data** to the internal backend API (`/api/v1/internal/sessions/{id}/output`) where the backend validates the schema, writes to MongoDB, and generates audit logs.

This gives you the best of both: low-latency status updates and centralized output validation.

---

# 13. API Design Philosophy

## 13.1 REST Principles

- Resources are nouns: `/sessions`, `/comments`, `/users`
- Actions are HTTP verbs: `GET`, `POST`, `DELETE`, `PATCH`
- Flow triggers are sub-resources: `/sessions/{id}/trigger/tipsc`
- Mentor actions are scoped: `/mentor/sessions`

## 13.2 Versioning Strategy

All routes are prefixed `/api/v1`. Version is in the URL, not headers, for maximum client compatibility and debuggability. v2 is introduced only for breaking changes.

## 13.3 Pagination

All list endpoints return paginated responses:

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 147,
    "has_next": true
  }
}
```

Default limit: 20. Maximum limit: 100. Cursor-based pagination is preferred for large collections (audit logs) over offset-based pagination.

## 13.4 Request ID and Correlation ID

Every request receives a `X-Request-ID` header (generated by middleware if not provided). Every response echoes it back. This allows end-to-end tracing from frontend log to backend log to Kafka event to worker log to DB write.

## 13.5 Idempotency Keys

`POST /sessions` accepts an optional `Idempotency-Key` header. If present and the key has been seen before (within 24 hours), return the original response without re-processing. This protects against double-submission from browser retries and network errors.

## 13.6 Standard Error Response Shape

```json
{
  "error": {
    "code": "SESSION_ALREADY_EXISTS",
    "message": "A session already exists for this student.",
    "request_id": "abc-123",
    "timestamp": "2026-06-01T10:00:00Z"
  }
}
```

Never expose stack traces, internal error messages, or MongoDB document IDs in error responses.

---

# 14. Error Handling

## 14.1 Exception Hierarchy

```
AppException (base)
├── AuthException
│   ├── InvalidCredentialsError (401)
│   ├── TokenExpiredError (401)
│   └── InsufficientPermissionsError (403)
├── SessionException
│   ├── SessionNotFoundError (404)
│   ├── SessionAlreadyExistsError (409)
│   └── InvalidStateTransitionError (409)
├── KafkaException
│   ├── KafkaPublishError (503)
│   └── KafkaTimeoutError (503)
├── DatabaseException
│   ├── DocumentNotFoundError (404)
│   ├── DuplicateKeyError (409)
│   └── DatabaseUnavailableError (503)
└── ValidationException (422)
```

## 14.2 Error Response Strategy

| Scenario                 | Response Code | Action                                                                |
| ------------------------ | ------------- | --------------------------------------------------------------------- |
| Missing required field   | 422           | Pydantic validation error, return field details                       |
| Invalid JWT              | 401           | Return`TOKEN_INVALID` error code                                    |
| Expired JWT              | 401           | Return`TOKEN_EXPIRED`, client refreshes                             |
| Wrong role               | 403           | Return`INSUFFICIENT_PERMISSIONS`                                    |
| Session not found        | 404           | Return`SESSION_NOT_FOUND`                                           |
| Duplicate session        | 409           | Return`SESSION_ALREADY_EXISTS`                                      |
| Invalid state transition | 409           | Return`INVALID_STATE_TRANSITION` with current state                 |
| Kafka unavailable        | 503           | Return`SERVICE_UNAVAILABLE`, do not corrupt DB state                |
| MongoDB timeout          | 503           | Return`DATABASE_UNAVAILABLE`                                        |
| Unhandled exception      | 500           | Log full trace internally, return generic`INTERNAL_ERROR` to client |

## 14.3 Retry Strategy

Kafka publish failures are retried internally (3 attempts with exponential backoff: 100ms, 300ms, 900ms). If all retries fail, the session status is rolled back and `503` is returned to the client.

MongoDB transient errors (connection reset, timeout) are retried similarly. Duplicate key errors are NOT retried — they represent a logic error and are returned as `409`.

## 14.4 Circuit Breaker

For the PES Auth API dependency, implement a circuit breaker:

- **Closed:** Normal operation.
- **Open:** PES API has failed 5 times in 30 seconds. All auth requests immediately return `503` without attempting to reach PES.
- **Half-Open:** After 60 seconds, allow one probe request. If it succeeds, close circuit.

---

# 15. Logging

## 15.1 Log Levels and Usage

| Level    | Usage                                                |
| -------- | ---------------------------------------------------- |
| DEBUG    | Detailed flow tracing (disabled in production)       |
| INFO     | Request received, event published, status changed    |
| WARNING  | Retry attempt, unexpected but recoverable condition  |
| ERROR    | Exception caught, operation failed, audit log missed |
| CRITICAL | System cannot function, requires immediate attention |

## 15.2 Structured Log Format

Every log entry is JSON:

```json
{
  "timestamp": "2026-06-01T10:00:00.123Z",
  "level": "INFO",
  "request_id": "abc-123",
  "correlation_id": "xyz-789",
  "user_id": "usr_001",
  "session_id": "ses_001",
  "endpoint": "POST /api/v1/sessions",
  "response_time_ms": 142,
  "status_code": 201,
  "message": "Session created successfully"
}
```

## 15.3 PII Masking

The logging middleware masks:

- `password` field (replace with `***`)
- JWT token values (log only the `sub` claim after decoding)
- SRN in URL paths (hash before logging)
- Any field named `token`, `secret`, `key`

Masking is applied before the log entry is written — never after.

## 15.4 Audit Log vs Application Log

| Property   | Application Log         | Audit Log                                 |
| ---------- | ----------------------- | ----------------------------------------- |
| Storage    | Log aggregation system  | MongoDB`audit_logs` collection          |
| Retention  | 30 days                 | Indefinite                                |
| Purpose    | Debugging, performance  | Compliance, traceability                  |
| Content    | Request details, errors | Business events                           |
| Mutability | Read-only after write   | Immutable — no updates, no deletes       |
| Querying   | Log search tool         | API endpoint (`/sessions/{id}/history`) |

---

# 16. Security

## 16.1 Authentication Security

- JWT signed with HS256, secret rotated quarterly.
- Access tokens: 15-minute TTL, stateless.
- Refresh tokens: 7-day TTL, stored hashed in DB, rotated on each use.
- Failed login rate limit: 5 attempts per minute per IP. Lockout after 10 failures.

## 16.2 Input Security

- All inputs pass Pydantic validation (type, length, format).
- Maximum payload size: 1MB (enforced at FastAPI/NGINX level).
- MongoDB operator injection prevention: never interpolate user input into raw MongoDB queries. All queries use parameterized Beanie ODM methods.
- HTML/script content in fields is stored as-is but escaped on output. The backend does not execute stored content.

## 16.3 CORS Configuration

- Allowed origins: only the deployed frontend URL (environment-specific).
- Methods: GET, POST, DELETE, PATCH, OPTIONS.
- Credentials: true (for cookie-based refresh tokens if adopted).
- Wildcard (`*`) origin is forbidden in production.

## 16.4 Secrets Management

- All secrets (JWT secret, MongoDB URI, Kafka credentials, PES Auth API key) live in environment variables.
- Never committed to version control.
- In production, sourced from a secrets manager (AWS Secrets Manager, HashiCorp Vault).
- Backend logs never emit environment variable names or values.

## 16.5 Secure Headers

Every response includes:

```
Strict-Transport-Security: max-age=63072000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'none'
X-Request-ID: <uuid>
```

## 16.6 Rate Limiting

| Endpoint                      | Limit                 |
| ----------------------------- | --------------------- |
| POST /auth/login              | 5 req/min per IP      |
| POST /sessions                | 3 req/min per user    |
| POST /sessions/{id}/trigger/* | 2 req/min per session |
| GET /sessions/{id} (polling)  | 30 req/min per user   |
| All others                    | 60 req/min per user   |

Limits are enforced in middleware using a sliding window counter stored in memory (or Redis in production).

---

# 17. Performance

## 17.1 Database Performance

- All query filters use indexed fields (see Section 8.3).
- The polling endpoint `GET /sessions/{id}` performs a single primary key lookup — O(1) with `_id` index.
- Mentor dashboard query (`GET /mentor/sessions`) uses the `team_id` index.
- Audit log queries use the compound `(session_id, timestamp)` index.
- Projection is used to fetch only required fields (never fetch entire documents for status-only checks).

## 17.2 Connection Pooling

- Motor (async MongoDB driver) uses a connection pool. Pool size: 10 connections per FastAPI worker.
- Kafka producer is a singleton — one producer per FastAPI instance, shared across requests.
- PES Auth API calls use an HTTP connection pool (httpx with `limits` configured).

## 17.3 Async I/O

- All I/O operations are `async/await` — MongoDB (Motor), HTTP (httpx), Kafka (aiokafka).
- No blocking calls (no `time.sleep`, no synchronous DB calls) in route handlers.
- Background tasks (audit log writes) use FastAPI's `BackgroundTasks` to avoid adding latency to the response.

## 17.4 Polling Optimization

With 100 concurrent users polling every 5 seconds, the backend receives ~1200 requests/minute on the GET endpoint. Optimizations:

1. Single indexed `_id` lookup — sub-millisecond.
2. Return only changed fields (use `If-None-Match` ETag header to allow 304 Not Modified responses when status hasn't changed).
3. Future: Redis cache with 2-second TTL for session status — reduces MongoDB reads by ~60%.

## 17.5 Payload Compression

Enable gzip compression for responses over 1KB. Most session documents (with embedded outputs) will be 5–50KB — compression reduces transfer time significantly for mobile clients.

---

# 18. Scalability

## 18.1 Stateless Backend

The FastAPI backend is stateless. All state lives in MongoDB or Kafka. Multiple backend instances can run behind a load balancer with zero configuration — no sticky sessions, no shared memory.

## 18.2 Horizontal Scaling Path

```
Internet
    │
    ▼
Load Balancer (NGINX / AWS ALB)
    │
    ├── FastAPI Instance 1
    ├── FastAPI Instance 2
    └── FastAPI Instance N
            │
            ▼
    MongoDB Atlas (replica set)
            │
    Kafka Cluster (3 brokers)
```

Scale FastAPI instances independently from Kafka workers. Workers scale based on Kafka consumer lag, not API traffic.

## 18.3 Database Scaling

- MongoDB Atlas auto-scales storage.
- Read replicas absorb polling and mentor dashboard queries.
- Atlas Search added for text search without additional infrastructure.
- Sharding by `team_id` when single-node capacity is reached.

## 18.4 Kafka Scaling

- Increase partitions on high-traffic topics.
- Add more worker instances (consumer group members) to parallelize processing.
- Backend publishing is unaffected by consumer scaling.

---

# 19. Edge Cases

## 19.1 Authentication Edge Cases

| #   | Scenario                               | Handling                                                                    |
| --- | -------------------------------------- | --------------------------------------------------------------------------- |
| A1  | Student submits wrong SRN format       | Pydantic validation rejects before PES API call                             |
| A2  | PES Auth API is down                   | 503 Service Unavailable with`PES_AUTH_UNAVAILABLE` code                   |
| A3  | PES Auth API times out (>5s)           | Circuit breaker opens, 503 returned                                         |
| A4  | JWT secret is rotated mid-day          | Tokens signed with old secret return 401; user must re-login                |
| A5  | Token used after logout                | Refresh token invalidated; access token expires naturally within 15 minutes |
| A6  | Token payload is tampered              | Signature verification fails, 401 returned                                  |
| A7  | `exp` claim missing from JWT         | Rejected — treat as invalid token                                          |
| A8  | Two simultaneous logins by same user   | Both succeed — last refresh token wins                                     |
| A9  | Brute force login attempts             | Rate limiter triggers after 5/min; lockout at 10 failures                   |
| A10 | Authorization header present but empty | 401 with`MISSING_TOKEN`                                                   |

## 19.2 Authorization Edge Cases

| #  | Scenario                                             | Handling                                                                 |
| -- | ---------------------------------------------------- | ------------------------------------------------------------------------ |
| B1 | Student accesses another team's session              | 403 Forbidden — ownership filter in repository                          |
| B2 | Mentor tries to trigger a flow                       | 403 Forbidden — role check in dependency                                |
| B3 | Student tries to access mentor endpoint              | 403 Forbidden                                                            |
| B4 | Admin tries to create a session as student           | 403 — Admin role cannot create sessions                                 |
| B5 | Mentor not assigned to a team tries to view sessions | Empty result set, not 403                                                |
| B6 | Student whose team was reassigned                    | JWT team_id is stale; refresh token flow re-issues JWT with correct team |

## 19.3 Session Edge Cases

| #   | Scenario                                                   | Handling                                               |
| --- | ---------------------------------------------------------- | ------------------------------------------------------ |
| C1  | Student double-clicks Submit (two simultaneous POSTs)      | Idempotency key deduplicates; only one session created |
| C2  | Student already has an active session and creates another  | 409 SESSION_ALREADY_EXISTS                             |
| C3  | Student submits empty problem statement                    | Pydantic validation rejects                            |
| C4  | Student submits 10MB text                                  | Payload size limit rejects at middleware layer         |
| C5  | Student submits`<script>alert(1)</script>` in idea field | Stored safely as string; escaped on output             |
| C6  | Session not found during GET                               | 404 SESSION_NOT_FOUND                                  |
| C7  | Student archives session while flow is running             | 409 CANNOT_ARCHIVE_ACTIVE_SESSION                      |
| C8  | Student creates new session without archiving old one      | 409 ACTIVE_SESSION_EXISTS                              |
| C9  | Frontend retries session creation on network error         | Idempotency key returns original session               |
| C10 | Session document grows very large (large AI output)        | Output is nested; projected fields limit query payload |

## 19.4 Kafka Edge Cases

| #  | Scenario                                                 | Handling                                                                                             |
| -- | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| D1 | Kafka broker is unavailable at publish time              | Retry 3x with backoff; if all fail, roll back session status, return 503                             |
| D2 | Kafka publish succeeds but DB update fails               | DB update is done before Kafka publish; this scenario means the event was never sent — retry safely |
| D3 | Same event published twice (retry after partial failure) | Workers deduplicate by`event_id`                                                                   |
| D4 | Wrong topic name used                                    | Configuration error caught at startup (topic validation)                                             |
| D5 | Kafka message exceeds broker max size                    | Payload size validated before publish; reject if too large                                           |
| D6 | Topic does not exist yet                                 | Topics created at startup via admin client                                                           |
| D7 | Backend Kafka producer crashes                           | FastAPI startup event re-initializes producer; requests queue in the meantime                        |
| D8 | Kafka cluster leader election in progress                | Producer retries with backoff during leadership transition                                           |

## 19.5 MongoDB Edge Cases

| #  | Scenario                                                   | Handling                                                                            |
| -- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| E1 | MongoDB connection pool exhausted                          | New requests receive 503; connection pool timeout returns error                     |
| E2 | Document not found during update                           | Repository returns False; service raises SessionNotFoundError → 404                |
| E3 | Duplicate key on session creation                          | 409 DUPLICATE_SESSION                                                               |
| E4 | Race condition: two updates to same session simultaneously | Optimistic concurrency (version field) detects conflict; loser retries              |
| E5 | MongoDB Atlas maintenance window                           | Connections fail; circuit breaker opens; 503 returned                               |
| E6 | Atlas read replica lag                                     | Polling requests may briefly show stale status (acceptable — eventual consistency) |
| E7 | Partial document write (power failure mid-operation)       | MongoDB's journaling ensures atomicity at document level                            |
| E8 | Index creation fails on startup                            | Backend fails to start; prevents corrupted index state                              |

## 19.6 Worker Edge Cases

| #  | Scenario                                                               | Handling                                                                              |
| -- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| F1 | Worker crashes mid-execution                                           | Status remains RUNNING; timeout watchdog marks as FAILED after N minutes              |
| F2 | Worker sends output for wrong session                                  | Backend validates`session_id` + `correlation_id` match; rejects mismatched update |
| F3 | Worker sends empty output`{}`                                        | Backend schema validation rejects empty output; session marked FAILED                 |
| F4 | Worker sends malformed JSON                                            | Parse error caught; session marked FAILED                                             |
| F5 | Worker tries to update a COMPLETED session                             | Backend rejects — invalid state transition                                           |
| F6 | Worker takes 20+ minutes                                               | Timeout threshold (configurable, default 15 min) marks session FAILED                 |
| F7 | Worker sends duplicate completion (Kafka replay)                       | Worker deduplicates by`event_id`; only first completion accepted                    |
| F8 | Worker writes to MongoDB directly with wrong schema                    | Beanie model validation rejects invalid fields                                        |
| F9 | Two workers pick up the same message (consumer group misconfiguration) | Only one consumer in a group receives a message; Kafka guarantees this                |

## 19.7 CrewAI Edge Cases

| #  | Scenario                                                       | Handling                                                                 |
| -- | -------------------------------------------------------------- | ------------------------------------------------------------------------ |
| G1 | CrewAI agent returns hallucinated extra fields                 | Output schema validation strips unknown fields or rejects                |
| G2 | CrewAI agent returns`"status": "DONE"` with no actual output | Backend schema validation requires non-empty output fields               |
| G3 | CrewAI agent times out                                         | Worker catches timeout, sets session to FAILED                           |
| G4 | CrewAI agent returns offensive content                         | Content policy agent (if implemented) intercepts; otherwise stored as-is |

## 19.8 Mentor Edge Cases

| #  | Scenario                                         | Handling                                                   |
| -- | ------------------------------------------------ | ---------------------------------------------------------- |
| H1 | Mentor submits 50,000 character comment          | Max comment length (2000 chars) enforced at Pydantic level |
| H2 | Mentor submits HTML in comment                   | Stored as string, escaped on API response                  |
| H3 | Student tries to delete mentor comment           | 403 Forbidden — ownership check                           |
| H4 | Mentor assigned to 50 teams fetches all sessions | Pagination enforced; query uses team_id index              |
| H5 | Mentor tries to trigger a flow                   | 403 Forbidden                                              |

## 19.9 Concurrency and Race Conditions

| #  | Scenario                                                 | Handling                                                       |
| -- | -------------------------------------------------------- | -------------------------------------------------------------- |
| I1 | Two trigger requests for same flow arrive simultaneously | State machine check + optimistic lock; second request gets 409 |
| I2 | Polling request arrives while worker is writing output   | MongoDB document-level atomicity ensures consistent read       |
| I3 | Worker writes completion while admin is deleting session | Soft-delete flag; worker update rejected for archived sessions |
| I4 | Kafka consumer rebalance during message processing       | Consumer commits offset only after successful DB write         |

## 19.10 Validation Edge Cases

| #  | Scenario                                         | Handling                                          |
| -- | ------------------------------------------------ | ------------------------------------------------- |
| J1 | Missing`Content-Type: application/json` header | FastAPI returns 415 Unsupported Media Type        |
| J2 | Non-UUID session_id in path                      | Pydantic path validator rejects invalid format    |
| J3 | Flow name not in allowed enum                    | Pydantic enum validation rejects; 422 returned    |
| J4 | Negative pagination offset                       | Pydantic constraint rejects values < 0            |
| J5 | `page=0` in pagination                         | Minimum page value is 1; enforced at schema level |

## 19.11 Security Edge Cases

| #  | Scenario                                              | Handling                                                                                |
| -- | ----------------------------------------------------- | --------------------------------------------------------------------------------------- |
| K1 | MongoDB injection via`$where` operator in JSON body | Beanie ODM never passes raw body to MongoDB operators                                   |
| K2 | JWT replay after password change                      | Short token TTL limits replay window; password change triggers refresh token revocation |
| K3 | Oversized Authorization header (header injection)     | Header size limit enforced at NGINX level                                               |
| K4 | CORS preflight from unauthorized origin               | CORS middleware rejects non-allowlisted origins                                         |
| K5 | Secret leaked in logs                                 | PII masking middleware strips secrets before log write                                  |

## 19.12 Recovery Edge Cases

| #  | Scenario                                       | Handling                                                                                                            |
| -- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| L1 | Backend restart with sessions in RUNNING state | On startup, scan for RUNNING sessions older than timeout threshold; mark as FAILED for retry                        |
| L2 | Kafka DLQ message cannot be processed          | Admin endpoint to inspect DLQ; manual replay or discard                                                             |
| L3 | Audit log write fails                          | Main operation succeeds; audit write retried in background (max 3 attempts); if all fail, logged to application log |
| L4 | MongoDB replica primary election               | Motor driver automatically reconnects to new primary; brief 503 during election                                     |

---

# 20. Future Improvements

## 20.1 Redis Caching

Add Redis as a caching layer between the backend and MongoDB:

- Cache `GET /sessions/{id}` responses with 2-second TTL — eliminates redundant MongoDB reads during polling.
- Cache RBAC lookups (mentor team assignments) with 60-second TTL.
- Store idempotency keys in Redis (faster than MongoDB for this use case).
- Store rate limit counters in Redis (required for multi-instance deployments — in-memory counters don't work with horizontal scaling).

## 20.2 WebSocket Notifications

Replace polling with WebSocket push:

- Student connects to `ws://backend/ws/sessions/{id}`.
- Backend pushes status change events as they occur.
- Eliminates 1200+ GET requests/minute from 100 users.
- Requires sticky sessions or a Redis pub/sub layer to broadcast from any backend instance to the correct WebSocket connection.

## 20.3 Outbox Pattern

The current approach publishes to Kafka synchronously during the request lifecycle. A production-grade improvement is the **Transactional Outbox Pattern**:

1. Write session to MongoDB.
2. Write Kafka event to an `outbox` MongoDB collection (same DB transaction).
3. A separate outbox poller reads from the `outbox` collection and publishes to Kafka.
4. After successful publish, mark outbox entry as `published`.

This eliminates the risk of a DB write succeeding while the Kafka publish fails — the event is never lost.

## 20.4 Prometheus + Grafana

Expose metrics endpoint:

- Request count per endpoint.
- Request latency (p50, p95, p99).
- Kafka producer error rate.
- MongoDB query latency.
- Active sessions by status.
- Worker queue depth (via Kafka consumer lag).

Grafana dashboards for ops team with alerts on error rate spikes, queue depth growth, and latency degradation.

## 20.5 OpenTelemetry Distributed Tracing

Instrument with OpenTelemetry:

- Every request generates a trace spanning: API handler → service → repository → MongoDB → Kafka.
- `correlation_id` becomes the trace ID.
- Traces are exported to Jaeger or Tempo.
- Worker spans are linked to the parent trace via propagated headers in Kafka message headers.

This enables end-to-end visibility: from the student clicking Submit to the CrewAI agent returning output.

## 20.6 SAGA Pattern for Multi-Step Flows

The current architecture triggers one flow at a time and relies on the student to manually advance between TIPSC → DFV → Discovery. A future SAGA orchestrator could:

- Automatically determine the next step after each completion.
- Handle compensating transactions if a mid-saga step fails.
- Allow the entire flow to run unattended once initiated.

## 20.7 CQRS (Command Query Responsibility Segregation)

Separate read and write models:

- **Write side:** FastAPI + MongoDB Atlas (primary) — all mutations go here.
- **Read side:** MongoDB read replica or Elasticsearch — all GET queries go here, optimized for search and filtering.

This allows independent scaling of read and write traffic. At current scale this is unnecessary, but worth implementing when the platform reaches thousands of concurrent mentors running dashboard queries.

## 20.8 API Gateway

Introduce an API Gateway (Kong, AWS API Gateway) in front of FastAPI:

- Centralized authentication (offload JWT validation from FastAPI).
- Rate limiting at infrastructure level.
- Request routing to multiple backend services as the platform grows.
- Built-in DDoS protection.

## 20.9 Event Sourcing

Replace the current state mutation model with event sourcing:

- Instead of storing `session.status = TIPSC_COMPLETED`, store an event `{ type: TIPSC_COMPLETED, timestamp, actor }`.
- Current state is derived by replaying events.
- Enables perfect audit trail and temporal debugging ("what was the session state at 10:03 AM?").
- Significant complexity increase — recommended only if the platform expands to require complex state reconstruction or compliance-grade auditability.

---

*This document is the authoritative reference for backend implementation. No implementation begins without this document being approved by team leads and the project owner. Any deviation from this architecture requires a written justification and an updated revision of this document.*

---

**Document Version History**

| Version | Date      | Author              | Changes                                         |
| ------- | --------- | ------------------- | ----------------------------------------------- |
| 1.0     | June 2026 | Backend Team        | Initial draft                                   |
| 2.0     | June 2026 | Principal Architect | Full architectural review, edge cases, patterns |

>>>>>>> Stashed changes
>>>>>>>
>>>>>>
>>>>>
>>>>
>>>
>>