# Backend Architecture Document

**Project:** AGIS Entrepreneurship Coach Platform
**Version:** 2.1
**Status:** Updated to match current implementation
**Date:** July 2026

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

| Concern | Owner |
|---------|-------|
| Authentication and JWT issuance | Backend |
| Role-Based Access Control enforcement | Backend |
| Session creation and lifecycle | Backend |
| State machine enforcement | Backend |
| MongoDB reads and writes (API path) | Backend |
| Kafka event publishing | Backend |
| Audit log generation | Backend |
| Mentor view APIs | Backend |
| Input validation | Backend |
| OpenAPI documentation | Backend |
| Worker result validation (internal API) | Backend |

## 1.3 What the Backend Must Never Do

| Concern | Why |
|---------|-----|
| Execute CrewAI agents | Agents are long-running, compute-heavy, would block event loop |
| Consume Kafka messages | Consumption is the Worker team's domain |
| Render or decide UI content | Frontend owns presentation logic |
| Call external AI APIs directly | All AI is encapsulated in agents, run only by workers |
| Make business decisions about AI output quality | Workers validate CrewAI output before writing to DB |

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
└──────────────┘     └──────────────────────┬─────────────────────┘
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
        │  { problem_statement, customer_segment, consequence, ... }
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
        ├── 7. Write session to MongoDB {status: created}
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
        └── (Optional) Call POST /api/v1/internal/sessions/{id}/output
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
    │   ├── history.py
    │   ├── worker.py
    │   └── common.py              # Pagination, BaseResponse, ErrorResponse
    │
    ├── models/                     # MongoDB document models (Beanie ODM)
    │   ├── user.py
    │   ├── team.py
    │   ├── session.py
    │   ├── audit.py
    │   └── comment.py
    │
    ├── repositories/               # All MongoDB interaction goes here — nothing else queries DB
    │   ├── base.py                # Generic CRUD base
    │   ├── session_repo.py
    │   ├── user_repo.py
    │   ├── audit_repo.py
    │   └── comment_repo.py
    │
    ├── services/                   # Business logic — routes call services, services call repos
    │   ├── auth_service.py        # PES Auth integration, JWT issuance
    │   ├── session_service.py     # Session lifecycle, state transitions
    │   ├── flow_service.py        # Flow trigger logic, state validation
    │   ├── audit_service.py       # Audit log writing
    │   ├── mentor_service.py      # Mentor-specific business rules
    │   ├── comment_service.py
    │   ├── history_service.py
    │   └── worker_service.py
    │
    ├── state_machine/              # Finite state machine — centralized, testable
    │   ├── states.py              # Enum of all states
    │   ├── transitions.py         # Allowed and forbidden transitions
    │   └── validator.py           # Validates transition before execution
    │
    ├── kafka/                      # Kafka producer only — no consumers here
    │   ├── producer.py            # aiokafka producer singleton
    │   ├── topics.py              # Topic name constants
    │   └── payloads.py            # Typed Pydantic payload schemas for events
    │
    ├── auth/                       # Authentication and authorization logic
    │   ├── jwt.py                 # Token creation, parsing, validation
    │   ├── pes_client.py          # HTTP client for PES Auth API
    │   └── dependencies.py        # FastAPI Depends() for current_user, require_role
    │
    ├── middleware/                 # Request lifecycle middleware
    │   ├── request_id.py          # Inject X-Request-ID into every request
    │   ├── correlation.py         # Propagate correlation IDs across layers
    │   ├── logging.py             # Structured request/response logging
    │   └── rate_limit.py          # Per-user rate limiting
    │
    ├── database/                   # Database connection and config
    │   ├── mongodb.py             # Motor/Beanie init, connection lifecycle
    │   └── indexes.py             # Index definitions — created on startup
    │
    ├── exceptions/                 # Custom exception hierarchy
    │   ├── base.py
    │   ├── auth.py
    │   ├── session.py
    │   ├── kafka.py
    │   └── handlers.py            # Global FastAPI exception handlers
    │
    ├── events/                     # Application lifecycle events
    │   ├── startup.py             # DB connect, Kafka producer init, index creation
    │   └── shutdown.py            # Graceful cleanup
    │
    ├── dependencies/               # FastAPI dependency injection
    │   ├── auth.py                # get_current_user, require_role
    │   ├── pagination.py
    │   └── session.py             # get_session_or_404
    │
    ├── logging/                    # Logging configuration
    │   ├── config.py              # structlog or logging setup
    │   └── masking.py             # PII/secret masking
    │
    ├── utils/                      # Pure utility functions
    │   ├── idempotency.py         # Idempotency key generation and checking
    │   ├── pagination.py
    │   ├── validators.py
    │   ├── object_id.py
    │   ├── response.py
    │   └── idempotency.py
    │
    ├── core/                       # System-wide constants and config
    │   ├── config.py              # Pydantic Settings — reads from env
    │   └── constants.py
    │
    ├── scripts/                    # Utility scripts
    │   ├── export_openapi.py
    │   ├── validate_openapi.py
    │   └── smoke_test.py
    │
    └── main.py                     # FastAPI app factory, router registration, middleware mounting
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

The backend validates all worker-produced updates before accepting them. Workers must send a `correlation_id` that matches what was published. A worker attempting to update a session in a terminal state (`COMPLETED`, `FAILED`) is rejected.

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
          │                  │ Student reviews TIPSC output
          ▼                  │
    ┌──────────┐             ▼
    │  RETRY   │    ┌──────────────────┐
    └──────────┘    │  DFV_WAITING     │ ← Student must trigger DFV manually
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

A student may start a new session only after archiving the current one. The previous session's scores are preserved in the DB (not deleted). The system does not delete old sessions.

---

# 6. State Machine

## 6.1 Allowed Transitions

| From State | Trigger | To State | Who Can Trigger |
|------------|---------|----------|-----------------|
| — | Student creates session | CREATED | Student |
| CREATED | Kafka publish succeeds | QUEUED | Backend (automatic) |
| QUEUED | Worker picks up | TIPSC_RUNNING | Worker |
| TIPSC_RUNNING | Worker succeeds | TIPSC_COMPLETED | Worker |
| TIPSC_RUNNING | Worker fails | TIPSC_FAILED | Worker |
| TIPSC_FAILED | Retry threshold not exceeded | QUEUED | Backend (retry) |
| TIPSC_COMPLETED | Student triggers DFV | DFV_WAITING | Backend (on student request) |
| DFV_WAITING | Worker picks up | DFV_RUNNING | Worker |
| DFV_RUNNING | Worker succeeds | DFV_COMPLETED | Worker |
| DFV_RUNNING | Worker fails | DFV_FAILED | Worker |
| DFV_COMPLETED | Student triggers discovery | DISCOVERY_WAITING | Backend |
| DISCOVERY_WAITING | Worker picks up | DISCOVERY_RUNNING | Worker |
| DISCOVERY_RUNNING | Worker succeeds | COMPLETED | Worker |
| DISCOVERY_RUNNING | Worker fails | DISCOVERY_FAILED | Worker |
| ANY (non-running) | Student archives | ARCHIVED | Student |

## 6.2 Forbidden Transitions

| Attempted Transition | Why Forbidden |
|---------------------|---------------|
| TIPSC_RUNNING → DFV_RUNNING | Cannot run two flows simultaneously |
| TIPSC_COMPLETED → TIPSC_RUNNING | Cannot re-run a completed flow |
| COMPLETED → any flow state | Session is terminal |
| ARCHIVED → any active state | Archived sessions are immutable |
| QUEUED → COMPLETED | Cannot skip states |
| DFV_WAITING → TIPSC_RUNNING | Cannot go backwards |

## 6.3 Enforcement

State validation is performed in `state_machine/validator.py`, called from `flow_service.py` before any Kafka publish or DB write. If the transition is forbidden, the service raises `InvalidStateTransitionError` which maps to `409 Conflict`.

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

| Collection | Purpose |
|------------|---------|
| `users` | One document per authenticated user |
| `teams` | One document per student team |
| `sessions` | One document per student session (core collection) |
| `audit_logs` | Immutable append-only event log |
| `mentor_comments` | Comments added by mentors |
| `refresh_tokens` | Opaque refresh tokens with expiry (TTL collection) |

## 8.2 Embedding vs Referencing Strategy

**Embed when:** The data is always read together, is bounded in size, and has no independent identity outside the parent.

**Reference when:** The data has its own lifecycle, can grow unboundedly, or is queried independently.

| Data | Strategy | Rationale |
|------|----------|-----------|
| TIPSC output in session | **Embed** | Always read with session, bounded, no independent queries |
| DFV output in session | **Embed** | Same as above |
| Discovery output in session | **Embed** | Same as above |
| Audit logs | **Separate collection** | Append-only, large volume, queried independently by timeline |
| Mentor comments | **Separate collection** | Can be deleted independently, queried independently |
| User in session | **Reference (user_id)** | User data is stable reference data |
| Team in session | **Reference (team_id)** | Team has its own lifecycle |

## 8.3 Index Strategy

| Collection | Index | Type | Reason |
|------------|-------|------|--------|
| sessions | `student_id` | Single | Fetch all sessions by student |
| sessions | `team_id` | Single | Mentor fetches team sessions |
| sessions | `status` | Single | Filter by state (admin, monitoring) |
| sessions | `(student_id, status)` | Compound | Active session lookup (most common query) |
| sessions | `created_at` | Single (desc) | Timeline ordering |
| audit_logs | `session_id` | Single | Fetch session history |
| audit_logs | `timestamp` | Single | Chronological ordering |
| audit_logs | `(session_id, timestamp)` | Compound | Timeline query for a session |
| mentor_comments | `session_id` | Single | Fetch comments for a session |
| refresh_tokens | `token_hash` | Single + Unique | Fast lookup during refresh |
| refresh_tokens | `expires_at` | TTL | Auto-delete expired tokens |

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
  + list_sessions(current_user: CurrentUser, filters: dict, page: int, limit: int) → (list[Session], total)
```

Services call repositories. Routes call services. Routes never call repositories.

## 9.3 Idempotency in Repositories

The `create` method accepts an optional `idempotency_key`. Before inserting, it checks whether a document with the same key exists. If it does, it returns the existing document. If not, it inserts. This is atomic via MongoDB's `findOneAndUpdate` with `upsert=True`.

---

# 10. Service Layer

## 10.1 Purpose

Services contain all business logic that is not HTTP-specific and not database-specific. They orchestrate repositories, state machine validation, Kafka publishing, and audit logging into coherent operations.

## 10.2 Service Responsibilities

| Service | Responsibilities |
|---------|-----------------|
| `AuthService` | Call PES API, generate JWT, handle refresh, validate token |
| `SessionService` | Create session, fetch session, archive session, validate ownership |
| `FlowService` | Validate state transition, publish Kafka event, update status |
| `AuditService` | Write audit log entries (fire-and-forget with retry) |
| `MentorService` | Fetch supervised teams, filter sessions by team, enforce mentor boundaries |
| `CommentService` | Create comment, validate comment length, enforce mentor-only creation |
| `HistoryService` | Fetch paginated audit history |
| `WorkerService` | Accept worker output/failure, validate correlation_id, update session |

## 10.3 Transaction-Like Behavior

MongoDB multi-document transactions are available but expensive. The preferred pattern for operations touching multiple collections is:

1. Write the primary document first.
2. Write the audit log second (can retry independently).
3. Publish Kafka event last (only after DB write confirms).

If Kafka publish fails, roll back the session status to its previous state in MongoDB. This ensures the user is never told "queued" when no event exists in Kafka.

---

# 11. Kafka Architecture

## 11.1 Topic Design

| Topic | Producer | Consumer | Purpose |
|-------|----------|----------|---------|
| `userSession.tipsc` | Backend | TIPSC Worker | Trigger TIPSC evaluation |
| `userSession.dfv` | Backend | DFV Worker | Trigger DFV evaluation |
| `userSession.discovery` | Backend | Discovery Worker | Trigger discovery planner |
| `userSession.notifications` | Workers | Notification Worker | Completion/failure signals |

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

- `event_id` is unique per publish. Workers use it for idempotency (deduplicate by `event_id`).
- `correlation_id` ties the entire request chain together (API call → Kafka event → worker execution → DB write).

## 11.3 Delivery Guarantees

| Property | Choice | Rationale |
|----------|--------|-----------|
| Delivery | At-least-once | Exactly-once requires distributed transactions; overkill here |
| Idempotency | Worker deduplication by `event_id` | Compensates for at-least-once delivery |
| Ordering | Per-partition ordering (partition by session_id) | Events for the same session always arrive in order |
| Retention | 7 days | Allows worker replay after outages |

## 11.4 Duplicate Publish Prevention

Before publishing, the backend:

1. Checks session status — if already `QUEUED` or `RUNNING`, rejects with `409`.
2. Uses an idempotency key (`session_id + flow + attempt_number`) to prevent double-publish from retry logic.
3. Wraps the DB status update and Kafka publish in a try/except. If Kafka fails, rolls back DB status.

## 11.5 Dead Letter Queue

Each topic has a companion DLQ:

| Topic | DLQ |
|-------|-----|
| `userSession.tipsc` | `userSession.tipsc.dlq` |
| `userSession.dfv` | `userSession.dfv.dlq` |
| `userSession.discovery` | `userSession.discovery.dlq` |

Workers send unprocessable messages to the DLQ after 3 failed attempts. The backend can query DLQ depth as part of the admin dashboard. Ops team manually inspects DLQ messages.

---

# 12. Worker Communication

## 12.1 Two Architecture Options

### Option A: Workers Write Directly to MongoDB

```
Worker → MongoDB (direct write)
```

**Pros:**
- Simpler — one fewer network hop
- Lower latency
- No backend availability dependency for worker completion

**Cons:**
- Workers must have MongoDB credentials (wider blast radius if compromised)
- Workers must know the DB schema intimately
- Schema changes require updating both backend and workers
- No centralized validation of worker output
- No automatic audit log generation for worker events

### Option B: Workers Call Internal Backend API

```
Worker → POST /api/v1/internal/sessions/{id}/output → Backend → MongoDB
```

**Pros:**
- Backend validates all worker output before it touches the DB
- Schema changes isolated to backend
- Workers don't need MongoDB credentials
- Audit logs generated by backend for worker completions
- Workers fully decoupled from persistence layer

**Cons:**
- One additional network hop
- Backend availability required for worker completion (minor — backend is highly available)
- Internal API must be secured (internal network + shared secret / service token)

## 12.2 Recommendation: Hybrid Approach

**Use a hybrid approach:**

- Workers write **execution status** (`RUNNING`, `COMPLETED`, `FAILED`) directly to MongoDB using a **separate service account** with write-only access to the `sessions.status` field only.
- Workers POST **output data** to the internal backend API (`/api/v1/internal/sessions/{id}/output`) where the backend validates the schema, writes to MongoDB, and generates audit logs.

This gives the best of both: low-latency status updates and centralized output validation.

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

| Scenario | Response Code | Action |
|----------|---------------|--------|
| Missing required field | 422 | Pydantic validation error, return field details |
| Invalid JWT | 401 | Return `TOKEN_INVALID` error code |
| Expired JWT | 401 | Return `TOKEN_EXPIRED`, client refreshes |
| Wrong role | 403 | Return `INSUFFICIENT_PERMISSIONS` |
| Session not found | 404 | Return `SESSION_NOT_FOUND` |
| Duplicate session | 409 | Return `SESSION_ALREADY_EXISTS` |
| Invalid state transition | 409 | Return `INVALID_STATE_TRANSITION` with current state |
| Kafka unavailable | 503 | Return `SERVICE_UNAVAILABLE`, do not corrupt DB state |
| MongoDB timeout | 503 | Return `DATABASE_UNAVAILABLE` |
| Unhandled exception | 500 | Log full trace internally, return generic `INTERNAL_ERROR` to client |

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

| Level | Usage |
|-------|-------|
| DEBUG | Detailed flow tracing (disabled in production) |
| INFO | Request received, event published, status changed |
| WARNING | Retry attempt, unexpected but recoverable condition |
| ERROR | Exception caught, operation failed, audit log missed |
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

| Property | Application Log | Audit Log |
|----------|-----------------|-----------|
| Storage | Log aggregation system | MongoDB `audit_logs` collection |
| Retention | 30 days | Indefinite |
| Purpose | Debugging, performance | Compliance, traceability |
| Content | Request details, errors | Business events |
| Mutability | Read-only after write | Immutable — no updates, no deletes |
| Querying | Log search tool | API endpoint (`/sessions/{id}/history`) |

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

| Endpoint | Limit |
|----------|-------|
| POST /auth/login | 5 req/min per IP |
| POST /sessions | 3 req/min per user |
| POST /sessions/{id}/trigger/* | 2 req/min per session |
| GET /sessions/{id} (polling) | 30 req/min per user |
| All others | 60 req/min per user |

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
            ▼
    Kafka Cluster
```

## 18.3 Worker Scaling

Workers are independently scalable. Each worker type (TIPSC, DFV, Discovery) can run multiple instances consuming from the same Kafka topic with the same consumer group ID. Kafka handles partition assignment automatically.

## 18.4 Database Scaling

- Read replicas for GET-heavy endpoints.
- Shard key on `team_id` if collection exceeds 100GB.
- Atlas Search for future full-text search.

---

# 19. Edge Cases

| # | Scenario | Correct Behavior |
|---|----------|------------------|
| E1 | Student with expired JWT attempts a request | `401 TOKEN_EXPIRED` — no RBAC check proceeds |
| E2 | Student accesses session that belongs to their team but different student | `404 SESSION_NOT_FOUND` — ownership is per-student, not per-team |
| E3 | Mentor reassigned to new team but JWT has old team IDs | JWT reflects stale `mentor_team_ids`. Next login issues corrected JWT. Until then, old teams visible, new team not visible. Acceptable given 15-min TTL. |
| E4 | Mentor tries to delete a comment they did not write | `403 INSUFFICIENT_PERMISSIONS` — comment ownership check fails |
| E5 | Admin tries to trigger TIPSC for a student | `403 INSUFFICIENT_PERMISSIONS` — flow triggers are student-only |
| E6 | Student sends `team_id` in request body to impersonate another team | `team_id` from body is ignored; only the `team_id` from verified JWT is used |
| E7 | Mentor submits request with a student's JWT (token sharing) | Request proceeds with the student role from JWT — mentor features unavailable |
| E8 | Worker sends request to user-facing endpoint with `X-Worker-Secret` header | Worker secret is not a valid JWT; `401 TOKEN_INVALID` returned |
| E9 | Student role embedded in JWT, but role changed in DB since login | JWT is the authority until it expires. DB role check is not performed per-request. Re-login refreshes role. |
| E10 | Two students in the same team — can Student A see Student B's session? | No. Sessions are scoped by `student_id`, not `team_id`. Even teammates cannot see each other's sessions. |
| E11 | Mentor attempts to add a comment to a session of an unassigned team | `404 SESSION_NOT_FOUND` — resource filter excludes the session before comment logic runs |
| E12 | Student submits `role: "admin"` in request body | Body fields cannot override JWT claims. Role is always extracted exclusively from the verified JWT. |

---

# 20. Future Improvements

- **WebSocket / SSE for real-time updates** — Replace polling with server-sent events or WebSockets for lower latency and reduced request volume.
- **Redis caching layer** — Cache session status with 2-second TTL to reduce MongoDB read load from polling.
- **Cursor-based pagination** — Replace offset-based pagination for audit logs and large collections.
- **OpenTelemetry integration** — Distributed tracing across frontend → backend → Kafka → worker → DB.
- **Automated DLQ replay tool** — Admin UI to inspect and replay dead-letter messages.
- **Rate limiting with Redis** — Move from in-memory to Redis-backed sliding window for multi-instance deployments.
- **API key authentication for server-to-server** — For future integrations beyond the frontend.
- **Comprehensive integration test suite** — Testcontainers for MongoDB + Kafka, full flow testing.
- **Schema registry for Kafka** — Avro/Protobuf schemas with Confluent Schema Registry for producer/consumer contract enforcement.