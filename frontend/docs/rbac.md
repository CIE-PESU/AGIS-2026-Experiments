
# Role-Based Access Control (RBAC)

**Project:** AGIS Entrepreneurship Coach Platform
**Version:** 1.0
**Applies To:** All backend API endpoints

---

## Table of Contents

1. [Overview](#1-overview)
2. [Roles](#2-roles)
3. [Role Assignment](#3-role-assignment)
4. [JWT Claims](#4-jwt-claims)
5. [Full Permission Matrix](#5-full-permission-matrix)
6. [Resource-Level Authorization](#6-resource-level-authorization)
7. [Enforcement Architecture](#7-enforcement-architecture)
8. [Forbidden Actions by Role](#8-forbidden-actions-by-role)
9. [RBAC Edge Cases](#9-rbac-edge-cases)
10. [Audit Logging for Auth Events](#10-audit-logging-for-auth-events)

---

## 1. Overview

RBAC on the AGIS platform enforces **two layers of access control** on every protected request:

**Layer 1 — Role Check:** Does this user's role permit access to this endpoint at all?

**Layer 2 — Resource Ownership Check:** Even if the role is permitted, does this specific user have the right to access this specific resource?

Both layers must pass. Passing Layer 1 alone is not sufficient.

```
Incoming Request
       │
       ▼
 JWT Validation
 (Is the token valid and not expired?)
       │
       ▼
 Role Extraction
 (What role does this user have?)
       │
       ▼
 Layer 1: Role Check
 (Is this role allowed on this endpoint?)
       │ Pass
       ▼
 Layer 2: Resource Ownership Check
 (Does this user own / have rights to this resource?)
       │ Pass
       ▼
 Business Logic Execution
```

If either check fails, the request is rejected with the appropriate error — no business logic executes.

---

## 2. Roles

### 2.1 Student

A student is an authenticated PESU user enrolled in the program. Students operate in **isolation** — they can only see, modify, and interact with their own workspace. They cannot view other students' sessions under any circumstance.

**Core Capabilities:**

- Create and manage their own session
- Trigger TIPSC, DFV, and Discovery flows
- View their own session status and outputs
- Read mentor comments on their own session
- Archive their own session

**Restrictions:**

- Cannot view any other student's session
- Cannot add comments (read-only on comments)
- Cannot view mentor dashboards
- Cannot trigger flows on behalf of anyone else
- Can only have **one active session at a time**

---

### 2.2 Mentor

A mentor is a faculty member or assigned guide. Mentors operate in **read-only mode** across sessions. They can add comments to sessions of teams they supervise. They have **zero ability to modify any session state or trigger any flow**.

**Core Capabilities:**

- View all sessions belonging to their assigned teams
- View full session output (TIPSC scores, DFV reports, Discovery plans)
- Add, edit, and delete their own comments
- Filter sessions by team and status
- View full audit history of supervised sessions

**Restrictions:**

- Cannot view sessions outside their assigned teams
- Cannot trigger any flow
- Cannot create or archive sessions
- Cannot edit or delete another mentor's comments
- Cannot access admin endpoints

---

### 2.3 Admin

An admin is a platform operator with full read and management access. Admins exist for operational oversight only — they do not participate in the student or mentor workflow.

**Core Capabilities:**

- View all sessions across all teams
- View full audit logs (system-wide)
- View platform metrics
- Archive any session
- Delete any comment
- Access all admin endpoints

**Restrictions:**

- Cannot create sessions (not a student role)
- Cannot trigger flows on behalf of a student
- Admin actions are fully audit-logged

---

### 2.4 Worker (Internal)

Workers are not human users. They authenticate via a shared internal secret (`X-Worker-Secret` header), not JWT. Worker access is restricted to internal network routes only and limited to two actions:

- `POST /api/v1/internal/sessions/{id}/output` — Submit completed flow output
- `POST /api/v1/internal/sessions/{id}/failure` — Report flow failure

Workers have **no access to any user-facing API endpoint**.

---

## 3. Role Assignment

Roles are assigned during user creation from PES Auth data:

| PES Auth User Type        | AGIS Role   |
| ------------------------- | ----------- |
| Student (SRN-based login) | `student` |
| Faculty / Mentor          | `mentor`  |
| Platform Administrator    | `admin`   |

Role is determined at login time. It is embedded in the JWT. Roles do not change mid-session — if a user's role changes, they must re-login to receive a new token.

A user cannot hold multiple roles simultaneously. A mentor cannot also be a student on the same platform account.

---

## 4. JWT Claims

Every issued JWT contains the following claims relevant to RBAC:

```json
{
  "sub": "usr_01J2K...",
  "role": "student",
  "team_id": "team_01J2K...",
  "mentor_team_ids": [],
  "srn": "PES2UG22CS001",
  "iat": 1748764800,
  "exp": 1748765700
}
```

| Claim               | Type      | Description                                                |
| ------------------- | --------- | ---------------------------------------------------------- |
| `sub`             | string    | Unique user ID                                             |
| `role`            | enum      | `student`, `mentor`, or `admin`                      |
| `team_id`         | string    | Team the student belongs to (null for mentors/admins)      |
| `mentor_team_ids` | array     | Team IDs the mentor supervises (empty for students/admins) |
| `srn`             | string    | Student registration number                                |
| `iat`             | timestamp | Token issued-at time                                       |
| `exp`             | timestamp | Token expiry (15 minutes from`iat`)                      |

**Why embed `team_id` and `mentor_team_ids` in the JWT?**

Embedding these values avoids a DB lookup on every request to determine what a user is allowed to see. The values are stable (team assignments don't change frequently) and the short TTL (15 minutes) ensures stale data is self-correcting.

---

## 5. Full Permission Matrix

### 5.1 Authentication Endpoints

| Endpoint               | Student | Mentor | Admin | Worker |
| ---------------------- | ------- | ------ | ----- | ------ |
| `POST /auth/login`   | ✅      | ✅     | ✅    | ❌     |
| `POST /auth/refresh` | ✅      | ✅     | ✅    | ❌     |
| `POST /auth/logout`  | ✅      | ✅     | ✅    | ❌     |
| `GET /auth/me`       | ✅      | ✅     | ✅    | ❌     |

---

### 5.2 Session Endpoints

| Endpoint                  | Student | Mentor | Admin | Notes                                              |
| ------------------------- | ------- | ------ | ----- | -------------------------------------------------- |
| `POST /sessions`        | ✅      | ❌     | ❌    | Student own only                                   |
| `GET /sessions`         | ✅      | ❌     | ✅    | Student sees own; Admin sees all                   |
| `GET /sessions/{id}`    | ✅      | ✅     | ✅    | Student: own; Mentor: supervised teams; Admin: all |
| `DELETE /sessions/{id}` | ✅      | ❌     | ✅    | Archive only; Student: own; Admin: any             |

---

### 5.3 Flow Trigger Endpoints

| Endpoint                                  | Student | Mentor | Admin | Notes                                         |
| ----------------------------------------- | ------- | ------ | ----- | --------------------------------------------- |
| `POST /sessions/{id}/trigger/tipsc`     | ✅      | ❌     | ❌    | Own session, valid state only                 |
| `POST /sessions/{id}/trigger/dfv`       | ✅      | ❌     | ❌    | Own session, TIPSC must be completed + passed |
| `POST /sessions/{id}/trigger/discovery` | ✅      | ❌     | ❌    | Own session, DFV must be completed            |

---

### 5.4 History Endpoints

| Endpoint                       | Student  | Mentor          | Admin |
| ------------------------------ | -------- | --------------- | ----- |
| `GET /sessions/{id}/history` | ✅ (own) | ✅ (supervised) | ✅    |

---

### 5.5 Comment Endpoints

| Endpoint                         | Student  | Mentor           | Admin | Notes                               |
| -------------------------------- | -------- | ---------------- | ----- | ----------------------------------- |
| `POST /sessions/{id}/comments` | ❌       | ✅               | ✅    | Mentor: supervised teams only       |
| `GET /sessions/{id}/comments`  | ✅ (own) | ✅ (supervised)  | ✅    | —                                  |
| `DELETE /comments/{id}`        | ❌       | ✅ (own comment) | ✅    | Mentor can only delete own comments |

---

### 5.6 Mentor Endpoints

| Endpoint                      | Student | Mentor          | Admin |
| ----------------------------- | ------- | --------------- | ----- |
| `GET /mentor/sessions`      | ❌      | ✅              | ✅    |
| `GET /mentor/sessions/{id}` | ❌      | ✅ (supervised) | ✅    |
| `GET /mentor/teams`         | ❌      | ✅              | ✅    |

---

### 5.7 Internal Worker Endpoints

| Endpoint                                 | Student | Mentor | Admin | Worker |
| ---------------------------------------- | ------- | ------ | ----- | ------ |
| `POST /internal/sessions/{id}/output`  | ❌      | ❌     | ❌    | ✅     |
| `POST /internal/sessions/{id}/failure` | ❌      | ❌     | ❌    | ✅     |

Internal endpoints are on a separate internal router. They are not mounted on the public-facing FastAPI app. They require `X-Worker-Secret` instead of `Authorization: Bearer`.

---

### 5.8 Health and Admin Endpoints

| Endpoint                | Student | Mentor | Admin | Public |
| ----------------------- | ------- | ------ | ----- | ------ |
| `GET /health`         | —      | —     | —    | ✅     |
| `GET /ready`          | —      | —     | —    | ✅     |
| `GET /live`           | —      | —     | —    | ✅     |
| `GET /admin/sessions` | ❌      | ❌     | ✅    | —     |
| `GET /admin/audit`    | ❌      | ❌     | ✅    | —     |
| `GET /admin/metrics`  | ❌      | ❌     | ✅    | —     |

---

## 6. Resource-Level Authorization

Role check alone is not enough. After confirming the role is permitted, the backend applies **resource ownership filters** to every data query.

### 6.1 Student Resource Filter

A student can only access resources where `student_id == current_user.user_id`.

Applied in `SessionRepository`:

```
find_session WHERE _id == session_id AND student_id == current_user.user_id
```

If the session exists but belongs to a different student, the repository returns `None`, which maps to a `404 SESSION_NOT_FOUND`. The client receives no indication that the session exists for someone else.

> Returning `404` instead of `403` on cross-student access is intentional. A `403` confirms the resource exists, which leaks information. A `404` reveals nothing.

### 6.2 Mentor Resource Filter

A mentor can only access resources where `team_id IN current_user.mentor_team_ids`.

Applied in `SessionRepository`:

```
find_sessions WHERE team_id IN [team_01, team_02, ...]
```

Mentors with no assigned teams receive an empty result set, not an error.

### 6.3 Admin Resource Filter

No ownership filter. Admins query all resources directly.

### 6.4 Comment Ownership Filter

For `DELETE /comments/{comment_id}`:

```
find_comment WHERE _id == comment_id AND mentor_id == current_user.user_id
```

Admins bypass this filter.

---

## 7. Enforcement Architecture

RBAC enforcement is handled in FastAPI's dependency injection layer — not inside route handler functions. This means authorization cannot be accidentally skipped.

### 7.1 Dependency Chain

```
Route Handler
    │
    └── Depends(get_session_for_student)
              │
              └── Depends(require_role(["student"]))
                        │
                        └── Depends(get_current_user)
                                  │
                                  └── Depends(verify_jwt_token)
```

Each dependency is resolved in order. If any fails, the chain stops and the appropriate error is returned.

### 7.2 Core Dependencies

**`verify_jwt_token`**
Extracts and validates the JWT from the `Authorization` header. Returns the decoded payload. Raises `401` on any failure.

**`get_current_user`**
Reads the `sub` claim from the JWT payload. Returns a typed `CurrentUser` object with `user_id`, `role`, `team_id`, `mentor_team_ids`.

**`require_role(roles: list[str])`**
Factory function. Returns a dependency that checks `current_user.role in roles`. Raises `403` if not.

Example usage in a route:

```python
@router.post("/sessions/{session_id}/trigger/tipsc")
async def trigger_tipsc(
    session_id: str,
    current_user: CurrentUser = Depends(require_role(["student"]))
):
    ...
```

**`get_session_or_404(session_id, current_user)`**
Fetches session from repository using the ownership-filtered query. Raises `404` if not found (covers both "doesn't exist" and "not yours" cases).

---

## 8. Forbidden Actions by Role

### 8.1 Actions Forbidden for Student

| Attempted Action                          | Endpoint                                | Response                         |
| ----------------------------------------- | --------------------------------------- | -------------------------------- |
| View mentor sessions dashboard            | `GET /mentor/sessions`                | `403 INSUFFICIENT_PERMISSIONS` |
| Add a comment to own session              | `POST /sessions/{id}/comments`        | `403 INSUFFICIENT_PERMISSIONS` |
| View another student's session            | `GET /sessions/{other_id}`            | `404 SESSION_NOT_FOUND`        |
| Trigger flow on another student's session | `POST /sessions/{other_id}/trigger/*` | `404 SESSION_NOT_FOUND`        |
| Access admin metrics                      | `GET /admin/metrics`                  | `403 INSUFFICIENT_PERMISSIONS` |
| Access worker internal endpoint           | `POST /internal/*`                    | `404` (not publicly mounted)   |

### 8.2 Actions Forbidden for Mentor

| Attempted Action                       | Endpoint                          | Response                         |
| -------------------------------------- | --------------------------------- | -------------------------------- |
| Create a session                       | `POST /sessions`                | `403 INSUFFICIENT_PERMISSIONS` |
| Trigger any flow                       | `POST /sessions/{id}/trigger/*` | `403 INSUFFICIENT_PERMISSIONS` |
| Archive a session                      | `DELETE /sessions/{id}`         | `403 INSUFFICIENT_PERMISSIONS` |
| View sessions outside supervised teams | `GET /sessions/{unrelated_id}`  | `404 SESSION_NOT_FOUND`        |
| Delete another mentor's comment        | `DELETE /comments/{other_id}`   | `403 INSUFFICIENT_PERMISSIONS` |
| Access admin endpoints                 | `GET /admin/*`                  | `403 INSUFFICIENT_PERMISSIONS` |

### 8.3 Actions Forbidden for Admin

| Attempted Action                | Endpoint                          | Response                         |
| ------------------------------- | --------------------------------- | -------------------------------- |
| Create a session                | `POST /sessions`                | `403 INSUFFICIENT_PERMISSIONS` |
| Trigger any flow                | `POST /sessions/{id}/trigger/*` | `403 INSUFFICIENT_PERMISSIONS` |
| Access worker internal endpoint | `POST /internal/*`              | `403` (worker secret required) |

---

## 9. RBAC Edge Cases

| #   | Scenario                                                                            | Correct Behavior                                                                                                                                          |
| --- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | Student with expired JWT attempts a request                                         | `401 TOKEN_EXPIRED` — no RBAC check proceeds                                                                                                           |
| R2  | Student accesses session that belongs to their own team but a different student     | `404 SESSION_NOT_FOUND` — ownership is per-student, not per-team                                                                                       |
| R3  | Mentor is reassigned to a new team but their JWT still has old team IDs             | JWT reflects stale`mentor_team_ids`. Next login issues corrected JWT. Until then, old teams visible, new team not visible. Acceptable given 15-min TTL. |
| R4  | Mentor tries to delete a comment they did not write                                 | `403 INSUFFICIENT_PERMISSIONS` — comment ownership check fails                                                                                         |
| R5  | Admin tries to trigger TIPSC for a student                                          | `403 INSUFFICIENT_PERMISSIONS` — flow triggers are student-only                                                                                        |
| R6  | Student sends`team_id` in the request body to impersonate another team            | `team_id` from body is ignored; only the `team_id` from verified JWT is used                                                                          |
| R7  | Mentor submits request with a student's JWT (token sharing)                         | Request proceeds with the student role from JWT — mentor features unavailable                                                                            |
| R8  | Worker sends a request to a user-facing endpoint with its`X-Worker-Secret` header | Worker secret is not a valid JWT;`401 TOKEN_INVALID` is returned                                                                                        |
| R9  | Student role embedded in JWT, but role changed in DB since login                    | JWT is the authority until it expires. DB role check is not performed per-request. Re-login refreshes role.                                               |
| R10 | Two students in the same team — can Student A see Student B's session?             | No. Sessions are scoped by`student_id`, not `team_id`. Even teammates cannot see each other's sessions.                                               |
| R11 | Mentor attempts to add a comment to a session of an unassigned team                 | `404 SESSION_NOT_FOUND` — resource filter excludes the session before comment logic runs                                                               |
| R12 | Student submits`role: "admin"` in the request body                                | Body fields cannot override JWT claims. Role is always extracted exclusively from the verified JWT.                                                       |

---

## 10. Audit Logging for Auth Events

Every authorization-relevant event generates an immutable audit log entry.

| Event                   | Trigger            | Logged Fields                                                                      |
| ----------------------- | ------------------ | ---------------------------------------------------------------------------------- |
| `LOGIN`               | Successful login   | `user_id`, `role`, `ip_address`, `timestamp`                               |
| `LOGIN_FAILED`        | Failed PES auth    | `srn`, `ip_address`, `reason`, `timestamp`                                 |
| `TOKEN_REFRESH`       | Successful refresh | `user_id`, `timestamp`                                                         |
| `LOGOUT`              | Explicit logout    | `user_id`, `timestamp`                                                         |
| `PERMISSION_DENIED`   | `403` returned   | `user_id`, `role`, `endpoint`, `session_id` (if applicable), `timestamp` |
| `UNAUTHORIZED_ACCESS` | `401` returned   | `endpoint`, `ip_address`, `reason`, `timestamp`                            |
| `ADMIN_ACTION`        | Any admin endpoint | `admin_id`, `action`, `target_resource`, `timestamp`                       |

Audit logs are **append-only**. They cannot be updated or deleted by any API — including admin endpoints. They are queryable via `GET /admin/audit`.

---

*This document governs all access control decisions on the AGIS backend. Any proposed change to roles, permissions, or ownership rules must be reflected here before implementation begins.*