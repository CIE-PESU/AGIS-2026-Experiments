
# API Specification

**Project:** AGIS Entrepreneurship Coach Platform
**Version:** v1
**Base URL:** `/api/v1`
**Authentication:** `Authorization: Bearer <JWT>`
**Content-Type:** `application/json`

---

## Table of Contents

1. [Standard Conventions](#1-standard-conventions)
2. [Authentication APIs](#2-authentication-apis)
3. [Session APIs](#3-session-apis)
4. [Flow Trigger APIs](#4-flow-trigger-apis)
5. [History APIs](#5-history-apis)
6. [Comment APIs](#6-comment-apis)
7. [Mentor APIs](#7-mentor-apis)
8. [Internal Worker APIs](#8-internal-worker-apis)
9. [Health APIs](#9-health-apis)
10. [Admin APIs](#10-admin-apis)
11. [Error Catalog](#11-error-catalog)
12. [Response Codes](#12-response-codes)

---

## 1. Standard Conventions

### 1.1 Request Headers

| Header               | Required                   | Description                                        |
| -------------------- | -------------------------- | -------------------------------------------------- |
| `Authorization`    | Yes (all protected routes) | `Bearer <access_token>`                          |
| `Content-Type`     | Yes (POST/PATCH)           | `application/json`                               |
| `Idempotency-Key`  | Optional                   | UUID to prevent duplicate submissions on POST      |
| `X-Request-ID`     | Optional                   | UUID echoed back in response for tracing           |
| `X-Correlation-ID` | Optional                   | Propagated across services for distributed tracing |

### 1.2 Response Envelope

**Success:**

```json
{
  "data": {},
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-06-01T10:00:00Z"
  }
}
```

**Paginated Success:**

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 147,
    "has_next": true,
    "has_prev": false
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-06-01T10:00:00Z"
  }
}
```

**Error:**

```json
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "No session found with the given ID.",
    "field": null,
    "request_id": "uuid",
    "timestamp": "2026-06-01T10:00:00Z"
  }
}
```

### 1.3 Pagination Query Parameters

| Parameter | Type    | Default        | Max | Description          |
| --------- | ------- | -------------- | --- | -------------------- |
| `page`  | integer | 1              | —  | Page number (min: 1) |
| `limit` | integer | 20             | 100 | Items per page       |
| `sort`  | string  | `created_at` | —  | Sort field           |
| `order` | string  | `desc`       | —  | `asc` or `desc`  |

---

## 2. Authentication APIs

### 2.1 Login

**Endpoint:** `POST /auth/login`
**Auth Required:** No
**Description:** Authenticates user via PES Auth API and returns JWT tokens.

**Request Body:**

```json
{
  "srn": "PES2UG22CS001",
  "password": "secret123"
}
```

| Field        | Type   | Required | Constraints                         |
| ------------ | ------ | -------- | ----------------------------------- |
| `srn`      | string | Yes      | Format:`PES2UG\d{2}[A-Z]{2}\d{3}` |
| `password` | string | Yes      | Min: 6 chars, Max: 128 chars        |

**Response `200`:**

```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "dGhpcyBpcyBhIHJhbmRvbSByZWZyZXNoIHRva2Vu",
    "token_type": "bearer",
    "expires_in": 900,
    "role": "student",
    "user": {
      "user_id": "usr_01J2K...",
      "name": "Sai Charan",
      "srn": "PES2UG22CS001",
      "team_id": "team_01J2K..."
    }
  }
}
```

**Errors:**

| Code | Error Code               | Condition                             |
| ---- | ------------------------ | ------------------------------------- |
| 401  | `INVALID_CREDENTIALS`  | Wrong SRN or password                 |
| 422  | `VALIDATION_ERROR`     | SRN format invalid                    |
| 503  | `PES_AUTH_UNAVAILABLE` | PES Auth API is down or timed out     |
| 429  | `RATE_LIMIT_EXCEEDED`  | More than 5 login attempts per minute |

---

### 2.2 Refresh Token

**Endpoint:** `POST /auth/refresh`
**Auth Required:** No
**Description:** Exchanges a valid refresh token for a new access token. Rotates the refresh token.

**Request Body:**

```json
{
  "refresh_token": "dGhpcyBpcyBhIHJhbmRvbSByZWZyZXNoIHRva2Vu"
}
```

**Response `200`:**

```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "bmV3cmVmcmVzaHRva2Vu",
    "expires_in": 900
  }
}
```

**Errors:**

| Code | Error Code                | Condition                                  |
| ---- | ------------------------- | ------------------------------------------ |
| 401  | `REFRESH_TOKEN_INVALID` | Token not found, already used, or tampered |
| 401  | `REFRESH_TOKEN_EXPIRED` | Token past its 7-day TTL                   |

---

### 2.3 Logout

**Endpoint:** `POST /auth/logout`
**Auth Required:** Yes
**Description:** Invalidates the refresh token server-side. The access token expires naturally.

**Request Body:**

```json
{
  "refresh_token": "dGhpcyBpcyBhIHJhbmRvbSByZWZyZXNoIHRva2Vu"
}
```

**Response `204`:** No content.

---

### 2.4 Get Current User

**Endpoint:** `GET /auth/me`
**Auth Required:** Yes
**Roles:** Student, Mentor, Admin
**Description:** Returns the profile of the currently authenticated user.

**Response `200`:**

```json
{
  "data": {
    "user_id": "usr_01J2K...",
    "name": "Sai Charan",
    "srn": "PES2UG22CS001",
    "email": "saicharan@pes.edu",
    "role": "student",
    "team_id": "team_01J2K..."
  }
}
```

---

## 3. Session APIs

### 3.1 Create Session

**Endpoint:** `POST /sessions`
**Auth Required:** Yes
**Roles:** Student only
**Description:** Creates a new session for the authenticated student. Publishes a TIPSC trigger to Kafka. A student can only have one active session.

**Request Body:**

```json
{
  "problem_statement": "Students in Tier-2 cities lack access to quality mentorship for entrepreneurship.",
  "idea": "A mobile-first platform that connects student founders with domain-expert mentors through structured 30-minute video sessions."
}
```

| Field                 | Type   | Required | Constraints                    |
| --------------------- | ------ | -------- | ------------------------------ |
| `problem_statement` | string | Yes      | Min: 50 chars, Max: 5000 chars |
| `idea`              | string | Yes      | Min: 50 chars, Max: 5000 chars |

**Headers:**

- `Idempotency-Key: <uuid>` — Strongly recommended to prevent duplicate sessions on network retry.

**Response `201`:**

```json
{
  "data": {
    "session_id": "ses_01J2K...",
    "status": "queued",
    "created_at": "2026-06-01T10:00:00Z"
  }
}
```

**Errors:**

| Code | Error Code                   | Condition                                |
| ---- | ---------------------------- | ---------------------------------------- |
| 400  | `VALIDATION_ERROR`         | Missing or too-short fields              |
| 403  | `INSUFFICIENT_PERMISSIONS` | Non-student role attempted               |
| 409  | `ACTIVE_SESSION_EXISTS`    | Student already has an active session    |
| 503  | `KAFKA_UNAVAILABLE`        | Kafka publish failed; session not queued |

---

### 3.2 Get Session by ID

**Endpoint:** `GET /sessions/{session_id}`
**Auth Required:** Yes
**Roles:** Student (own), Mentor (supervised team), Admin
**Description:** Returns the full session document including all flow outputs.

**Path Parameters:**

| Parameter      | Type   | Description             |
| -------------- | ------ | ----------------------- |
| `session_id` | string | The session's unique ID |

**Response `200`:**

```json
{
  "data": {
    "session_id": "ses_01J2K...",
    "team_id": "team_01J2K...",
    "student_id": "usr_01J2K...",
    "problem_statement": "Students in Tier-2 cities...",
    "idea": "A mobile-first platform...",
    "status": "tipsc_completed",
    "tipsc": {
      "status": "completed",
      "score": {
        "timing": 8,
        "idea": 7,
        "problem": 9,
        "solution": 8,
        "competition": 6
      },
      "total_score": 38,
      "ready_for_dfv": true,
      "compliance_flag": true,
      "compliance_issues": [],
      "followups_asked": 1,
      "reasoning": "The idea is timely given the growth in EdTech...",
      "completed_at": "2026-06-01T10:05:00Z"
    },
    "dfv": null,
    "discovery": null,
    "created_at": "2026-06-01T10:00:00Z",
    "updated_at": "2026-06-01T10:05:00Z"
  }
}
```

**Errors:**

| Code | Error Code                   | Condition                                |
| ---- | ---------------------------- | ---------------------------------------- |
| 404  | `SESSION_NOT_FOUND`        | No session with this ID                  |
| 403  | `INSUFFICIENT_PERMISSIONS` | Student accessing another team's session |

---

### 3.3 List Student Sessions

**Endpoint:** `GET /sessions`
**Auth Required:** Yes
**Roles:** Student (own sessions), Admin (all)
**Description:** Returns paginated list of sessions for the authenticated student.

**Query Parameters:**

| Parameter  | Type    | Default | Description      |
| ---------- | ------- | ------- | ---------------- |
| `page`   | integer | 1       | Page number      |
| `limit`  | integer | 20      | Items per page   |
| `status` | string  | —      | Filter by status |

**Response `200`:**

```json
{
  "data": [
    {
      "session_id": "ses_01J2K...",
      "status": "tipsc_completed",
      "problem_statement": "Students in Tier-2 cities...",
      "created_at": "2026-06-01T10:00:00Z",
      "updated_at": "2026-06-01T10:05:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 3,
    "has_next": false,
    "has_prev": false
  }
}
```

---

### 3.4 Archive Session

**Endpoint:** `DELETE /sessions/{session_id}`
**Auth Required:** Yes
**Roles:** Student (own), Admin
**Description:** Soft-archives a session. The session data is preserved and queryable via history. A student must archive their current session before starting a new one. Cannot archive a session while a flow is running.

**Response `200`:**

```json
{
  "data": {
    "session_id": "ses_01J2K...",
    "status": "archived",
    "archived_at": "2026-06-01T11:00:00Z"
  }
}
```

**Errors:**

| Code | Error Code                        | Condition                           |
| ---- | --------------------------------- | ----------------------------------- |
| 409  | `CANNOT_ARCHIVE_ACTIVE_SESSION` | A flow is currently running         |
| 404  | `SESSION_NOT_FOUND`             | Session does not exist              |
| 403  | `INSUFFICIENT_PERMISSIONS`      | Accessing another student's session |

---

## 4. Flow Trigger APIs

### 4.1 Trigger TIPSC

**Endpoint:** `POST /sessions/{session_id}/trigger/tipsc`**Auth Required:** Yes**Roles:** Student (own session)**Description:** Triggers the TIPSC evaluation flow. Only valid when session status is `created` or `queued`. Publishes to `userSession.tipsc` Kafka topic.

> This is typically triggered automatically on session creation. This endpoint exists for retry scenarios where the initial publish failed.

**Response `200`:**

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

**Errors:**

| Code | Error Code                   | Condition                                        |
| ---- | ---------------------------- | ------------------------------------------------ |
| 409  | `INVALID_STATE_TRANSITION` | Session not in a state that allows TIPSC trigger |
| 409  | `FLOW_ALREADY_RUNNING`     | TIPSC is already running                         |
| 503  | `KAFKA_UNAVAILABLE`        | Kafka publish failed                             |

---

### 4.2 Trigger DFV

**Endpoint:** `POST /sessions/{session_id}/trigger/dfv`
**Auth Required:** Yes
**Roles:** Student (own session)
**Description:** Triggers the DFV evaluation flow. Only valid when session status is `tipsc_completed` and `tipsc.ready_for_dfv == true`. Student must provide DFV context inputs. Publishes to `userSession.dfv` Kafka topic.

**Request Body:**

```json
{
  "desirability_context": "We conducted 20 customer interviews. 85% of students said they would pay for a mentorship platform. Key pain: no one-on-one guidance available locally.",
  "feasibility_context": "MVP can be built in 8 weeks with a 3-person team. We have access to React, FastAPI, and Agora for video. Estimated infra cost: $200/month.",
  "viability_context": "Subscription model: Rs. 499/month per student. TAM is 2M engineering students in India. Break-even at 1000 subscribers. LTV estimated at Rs. 6000."
}
```

| Field                    | Type   | Required | Constraints                     |
| ------------------------ | ------ | -------- | ------------------------------- |
| `desirability_context` | string | Yes      | Min: 100 chars, Max: 3000 chars |
| `feasibility_context`  | string | Yes      | Min: 100 chars, Max: 3000 chars |
| `viability_context`    | string | Yes      | Min: 100 chars, Max: 3000 chars |

**Response `200`:**

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

**Errors:**

| Code | Error Code                   | Condition                         |
| ---- | ---------------------------- | --------------------------------- |
| 409  | `INVALID_STATE_TRANSITION` | TIPSC not completed or not passed |
| 409  | `DFV_NOT_UNLOCKED`         | `tipsc.ready_for_dfv` is false  |
| 503  | `KAFKA_UNAVAILABLE`        | Kafka publish failed              |

---

### 4.3 Trigger Discovery Planner

**Endpoint:** `POST /sessions/{session_id}/trigger/discovery`
**Auth Required:** Yes
**Roles:** Student (own session)
**Description:** Triggers the Customer Discovery Planner flow. Only valid when session status is `dfv_completed`. Publishes to `userSession.discovery` Kafka topic.

**Response `200`:**

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

**Errors:**

| Code | Error Code                   | Condition            |
| ---- | ---------------------------- | -------------------- |
| 409  | `INVALID_STATE_TRANSITION` | DFV not completed    |
| 503  | `KAFKA_UNAVAILABLE`        | Kafka publish failed |

---

## 5. History APIs

### 5.1 Get Session History

**Endpoint:** `GET /sessions/{session_id}/history`
**Auth Required:** Yes
**Roles:** Student (own), Mentor (supervised team), Admin
**Description:** Returns the full chronological audit trail for a session — all state transitions, triggers, completions, and comments.

**Query Parameters:**

| Parameter | Type    | Default | Description               |
| --------- | ------- | ------- | ------------------------- |
| `page`  | integer | 1       | Page number               |
| `limit` | integer | 50      | Items per page (max: 200) |

**Response `200`:**

```json
{
  "data": [
    {
      "event_id": "evt_01J2K...",
      "session_id": "ses_01J2K...",
      "event": "SESSION_CREATED",
      "actor": "usr_01J2K...",
      "actor_role": "student",
      "metadata": {
        "problem_statement_length": 120
      },
      "timestamp": "2026-06-01T10:00:00Z"
    },
    {
      "event_id": "evt_01J2K...",
      "session_id": "ses_01J2K...",
      "event": "TIPSC_TRIGGERED",
      "actor": "usr_01J2K...",
      "actor_role": "student",
      "metadata": {
        "correlation_id": "cor_01J2K...",
        "kafka_topic": "userSession.tipsc"
      },
      "timestamp": "2026-06-01T10:00:01Z"
    },
    {
      "event_id": "evt_01J2K...",
      "session_id": "ses_01J2K...",
      "event": "TIPSC_COMPLETED",
      "actor": "worker_tipsc",
      "actor_role": "worker",
      "metadata": {
        "total_score": 38,
        "ready_for_dfv": true,
        "duration_seconds": 287
      },
      "timestamp": "2026-06-01T10:04:48Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 8,
    "has_next": false,
    "has_prev": false
  }
}
```

**Audit Event Types:**

| Event                   | Triggered By     | Description              |
| ----------------------- | ---------------- | ------------------------ |
| `SESSION_CREATED`     | Student          | New session created      |
| `TIPSC_TRIGGERED`     | Student / System | TIPSC flow triggered     |
| `TIPSC_RUNNING`       | Worker           | Worker started TIPSC     |
| `TIPSC_COMPLETED`     | Worker           | TIPSC output written     |
| `TIPSC_FAILED`        | Worker / System  | TIPSC encountered error  |
| `DFV_TRIGGERED`       | Student          | DFV flow triggered       |
| `DFV_RUNNING`         | Worker           | Worker started DFV       |
| `DFV_COMPLETED`       | Worker           | DFV output written       |
| `DFV_FAILED`          | Worker / System  | DFV encountered error    |
| `DISCOVERY_TRIGGERED` | Student          | Discovery triggered      |
| `DISCOVERY_RUNNING`   | Worker           | Worker started discovery |
| `DISCOVERY_COMPLETED` | Worker           | Discovery output written |
| `DISCOVERY_FAILED`    | Worker / System  | Discovery failed         |
| `COMMENT_ADDED`       | Mentor           | Mentor added a comment   |
| `COMMENT_DELETED`     | Mentor / Admin   | Comment removed          |
| `SESSION_ARCHIVED`    | Student / Admin  | Session archived         |
| `RETRY_TRIGGERED`     | System           | Auto-retry initiated     |
| `LOGIN`               | User             | Successful login         |

---

## 6. Comment APIs

### 6.1 Add Comment

**Endpoint:** `POST /sessions/{session_id}/comments`
**Auth Required:** Yes
**Roles:** Mentor, Admin
**Description:** Adds a mentor comment to a session. Only mentors supervising the session's team can comment.

**Request Body:**

```json
{
  "comment": "Strong problem definition. Recommend tightening the competitive analysis — there are 3 established players in this space that need to be addressed before DFV."
}
```

| Field       | Type   | Required | Constraints                                      |
| ----------- | ------ | -------- | ------------------------------------------------ |
| `comment` | string | Yes      | Min: 10 chars, Max: 2000 chars. HTML is escaped. |

**Response `201`:**

```json
{
  "data": {
    "comment_id": "cmt_01J2K...",
    "session_id": "ses_01J2K...",
    "mentor_id": "usr_mentor_01",
    "mentor_name": "Prof. Sharma",
    "comment": "Strong problem definition...",
    "created_at": "2026-06-01T10:15:00Z"
  }
}
```

**Errors:**

| Code | Error Code                   | Condition                                         |
| ---- | ---------------------------- | ------------------------------------------------- |
| 403  | `INSUFFICIENT_PERMISSIONS` | Not a mentor, or mentor not assigned to this team |
| 404  | `SESSION_NOT_FOUND`        | Session does not exist                            |

---

### 6.2 Get Comments

**Endpoint:** `GET /sessions/{session_id}/comments`
**Auth Required:** Yes
**Roles:** Student (own), Mentor (supervised team), Admin
**Description:** Returns all mentor comments for a session in chronological order.

**Response `200`:**

```json
{
  "data": [
    {
      "comment_id": "cmt_01J2K...",
      "mentor_name": "Prof. Sharma",
      "comment": "Strong problem definition...",
      "created_at": "2026-06-01T10:15:00Z"
    }
  ]
}
```

---

### 6.3 Delete Comment

**Endpoint:** `DELETE /comments/{comment_id}`
**Auth Required:** Yes
**Roles:** Mentor (own comment only), Admin
**Description:** Soft-deletes a mentor comment. Only the comment author or an admin can delete.

**Response `204`:** No content.

**Errors:**

| Code | Error Code                   | Condition                      |
| ---- | ---------------------------- | ------------------------------ |
| 403  | `INSUFFICIENT_PERMISSIONS` | Not the comment owner or admin |
| 404  | `COMMENT_NOT_FOUND`        | Comment does not exist         |

---

## 7. Mentor APIs

### 7.1 List Mentor Sessions

**Endpoint:** `GET /mentor/sessions`
**Auth Required:** Yes
**Roles:** Mentor only
**Description:** Returns all sessions belonging to teams supervised by the authenticated mentor. Supports filtering by status and team.

**Query Parameters:**

| Parameter   | Type    | Description               |
| ----------- | ------- | ------------------------- |
| `team_id` | string  | Filter by specific team   |
| `status`  | string  | Filter by session status  |
| `page`    | integer | Page number               |
| `limit`   | integer | Items per page (max: 100) |

**Response `200`:**

```json
{
  "data": [
    {
      "session_id": "ses_01J2K...",
      "team_id": "team_01J2K...",
      "team_name": "Team Ignite",
      "student_name": "Sai Charan",
      "status": "tipsc_completed",
      "tipsc_score": 38,
      "ready_for_dfv": true,
      "created_at": "2026-06-01T10:00:00Z",
      "updated_at": "2026-06-01T10:05:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 12,
    "has_next": false,
    "has_prev": false
  }
}
```

---

### 7.2 Get Mentor Session Detail

**Endpoint:** `GET /mentor/sessions/{session_id}`
**Auth Required:** Yes
**Roles:** Mentor (supervised team only)
**Description:** Returns the full session detail including all flow outputs. Same shape as `GET /sessions/{session_id}` but enforces mentor scoping.

---

### 7.3 List Mentor Teams

**Endpoint:** `GET /mentor/teams`
**Auth Required:** Yes
**Roles:** Mentor only
**Description:** Returns the list of teams assigned to the authenticated mentor.

**Response `200`:**

```json
{
  "data": [
    {
      "team_id": "team_01J2K...",
      "team_name": "Team Ignite",
      "member_count": 3,
      "active_session_count": 1,
      "members": [
        {
          "user_id": "usr_01J2K...",
          "name": "Sai Charan",
          "srn": "PES2UG22CS001"
        }
      ]
    }
  ]
}
```

---

## 8. Internal Worker APIs

> These endpoints are **not exposed publicly**. They are only reachable from the internal network by worker services. They require a `X-Worker-Secret` header in addition to being on a private network route.

### 8.1 Submit Flow Output

**Endpoint:** `POST /internal/sessions/{session_id}/output`
**Auth Required:** Worker secret header
**Description:** Workers call this after successfully completing a flow. The backend validates the output schema, writes to MongoDB, updates session status, and generates audit logs.

**Headers:**

```
X-Worker-Secret: <shared_internal_secret>
X-Worker-ID: tipsc-worker-01
X-Correlation-ID: cor_01J2K...
```

**Request Body (TIPSC):**

```json
{
  "flow": "tipsc",
  "correlation_id": "cor_01J2K...",
  "status": "completed",
  "output": {
    "score": {
      "timing": 8,
      "idea": 7,
      "problem": 9,
      "solution": 8,
      "competition": 6
    },
    "total_score": 38,
    "ready_for_dfv": true,
    "compliance_flag": true,
    "compliance_issues": [],
    "followups_asked": 1,
    "reasoning": "The idea is timely..."
  },
  "duration_seconds": 287
}
```

**Request Body (DFV):**

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
  "duration_seconds": 412
}
```

**Request Body (Discovery):**

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
  "duration_seconds": 310
}
```

**Response `200`:**

```json
{
  "data": {
    "accepted": true,
    "session_id": "ses_01J2K...",
    "new_status": "tipsc_completed"
  }
}
```

**Errors:**

| Code | Error Code                   | Condition                                          |
| ---- | ---------------------------- | -------------------------------------------------- |
| 400  | `INVALID_OUTPUT_SCHEMA`    | Output missing required fields                     |
| 409  | `INVALID_STATE_TRANSITION` | Worker trying to update completed/archived session |
| 409  | `CORRELATION_ID_MISMATCH`  | Correlation ID does not match published event      |
| 403  | `INVALID_WORKER_SECRET`    | Worker secret header invalid                       |

---

### 8.2 Report Flow Failure

**Endpoint:** `POST /internal/sessions/{session_id}/failure`
**Auth Required:** Worker secret header
**Description:** Workers call this when a flow fails after exhausting retries.

**Request Body:**

```json
{
  "flow": "tipsc",
  "correlation_id": "cor_01J2K...",
  "error_code": "CREWAI_TIMEOUT",
  "error_message": "Agent did not respond within 15 minutes",
  "retry_count": 3
}
```

**Response `200`:**

```json
{
  "data": {
    "accepted": true,
    "session_id": "ses_01J2K...",
    "new_status": "tipsc_failed"
  }
}
```

---

## 9. Health APIs

### 9.1 Health Check

**Endpoint:** `GET /health`
**Auth Required:** No
**Description:** Returns overall system health. Used by load balancers and uptime monitors.

**Response `200`:**

```json
{
  "status": "healthy",
  "timestamp": "2026-06-01T10:00:00Z",
  "services": {
    "mongodb": "connected",
    "kafka_producer": "connected",
    "pes_auth": "reachable"
  }
}
```

**Response `503` (degraded):**

```json
{
  "status": "degraded",
  "timestamp": "2026-06-01T10:00:00Z",
  "services": {
    "mongodb": "connected",
    "kafka_producer": "disconnected",
    "pes_auth": "reachable"
  }
}
```

---

### 9.2 Readiness Probe

**Endpoint:** `GET /ready`
**Auth Required:** No
**Description:** Returns `200` only when the backend is fully initialized and ready to serve traffic (DB connected, Kafka producer ready, indexes created).

---

### 9.3 Liveness Probe

**Endpoint:** `GET /live`
**Auth Required:** No
**Description:** Returns `200` as long as the process is running. Used by Kubernetes liveness probe.

---

## 10. Admin APIs

> Accessible by `admin` role only.

### 10.1 Get All Sessions

**Endpoint:** `GET /admin/sessions`
**Auth Required:** Yes (Admin)
**Description:** Paginated list of all sessions across all teams with filter support.

**Query Parameters:** `status`, `team_id`, `student_id`, `page`, `limit`, `sort`, `order`

---

### 10.2 Get Audit Log

**Endpoint:** `GET /admin/audit`
**Auth Required:** Yes (Admin)
**Description:** System-wide audit log with filter support.

**Query Parameters:** `event`, `actor`, `session_id`, `from`, `to`, `page`, `limit`

---

### 10.3 Get Metrics

**Endpoint:** `GET /admin/metrics`
**Auth Required:** Yes (Admin)
**Description:** Returns operational metrics.

**Response `200`:**

```json
{
  "data": {
    "active_sessions": 47,
    "sessions_by_status": {
      "queued": 3,
      "tipsc_running": 5,
      "tipsc_completed": 20,
      "dfv_running": 2,
      "dfv_completed": 10,
      "completed": 7,
      "failed": 2,
      "archived": 12
    },
    "total_logins_today": 93,
    "kafka_publish_errors_last_hour": 0,
    "average_tipsc_duration_seconds": 312
  }
}
```

---

## 11. Error Catalog

| Error Code                        | HTTP Status | Description                                      | Action                               |
| --------------------------------- | ----------- | ------------------------------------------------ | ------------------------------------ |
| `INVALID_CREDENTIALS`           | 401         | SRN or password is wrong                         | Re-enter credentials                 |
| `TOKEN_INVALID`                 | 401         | JWT is malformed or signature mismatch           | Re-login                             |
| `TOKEN_EXPIRED`                 | 401         | JWT access token has expired                     | Use refresh token                    |
| `REFRESH_TOKEN_INVALID`         | 401         | Refresh token not found or tampered              | Re-login                             |
| `REFRESH_TOKEN_EXPIRED`         | 401         | Refresh token past 7-day TTL                     | Re-login                             |
| `INSUFFICIENT_PERMISSIONS`      | 403         | Role not allowed for this endpoint               | Contact admin                        |
| `SESSION_NOT_FOUND`             | 404         | No session with the given ID exists              | Check session ID                     |
| `COMMENT_NOT_FOUND`             | 404         | No comment with the given ID exists              | Check comment ID                     |
| `USER_NOT_FOUND`                | 404         | User record not found                            | Contact admin                        |
| `ACTIVE_SESSION_EXISTS`         | 409         | Student already has an active session            | Archive existing session first       |
| `SESSION_ALREADY_EXISTS`        | 409         | Idempotency key matched an existing session      | Use original response                |
| `INVALID_STATE_TRANSITION`      | 409         | Flow trigger not valid for current session state | Check current session status         |
| `FLOW_ALREADY_RUNNING`          | 409         | A flow is already running on this session        | Wait for completion                  |
| `DFV_NOT_UNLOCKED`              | 409         | TIPSC did not pass`ready_for_dfv`              | Review TIPSC output                  |
| `CANNOT_ARCHIVE_ACTIVE_SESSION` | 409         | Session has a flow currently running             | Wait for flow to complete            |
| `CORRELATION_ID_MISMATCH`       | 409         | Worker correlation ID does not match             | Worker bug — investigate            |
| `INVALID_OUTPUT_SCHEMA`         | 400         | Worker output missing required fields            | Worker bug — investigate            |
| `VALIDATION_ERROR`              | 422         | Request body failed Pydantic validation          | Fix request payload                  |
| `RATE_LIMIT_EXCEEDED`           | 429         | Too many requests                                | Slow down requests                   |
| `PES_AUTH_UNAVAILABLE`          | 503         | PES Auth API is down or timed out                | Retry after delay                    |
| `KAFKA_UNAVAILABLE`             | 503         | Kafka publish failed after retries               | Retry later                          |
| `DATABASE_UNAVAILABLE`          | 503         | MongoDB connection failed                        | Retry later                          |
| `INTERNAL_ERROR`                | 500         | Unhandled exception                              | Contact backend team with request_id |

---

## 12. Response Codes

| Code    | Meaning               | When Used                                           |
| ------- | --------------------- | --------------------------------------------------- |
| `200` | OK                    | Successful GET, successful trigger                  |
| `201` | Created               | Session created, comment created                    |
| `204` | No Content            | Logout, delete comment                              |
| `400` | Bad Request           | Malformed request, invalid output from worker       |
| `401` | Unauthorized          | Missing, invalid, or expired token                  |
| `403` | Forbidden             | Valid token but insufficient role or ownership      |
| `404` | Not Found             | Resource does not exist                             |
| `409` | Conflict              | Duplicate submission, invalid state transition      |
| `422` | Unprocessable Entity  | Pydantic validation failure                         |
| `429` | Too Many Requests     | Rate limit exceeded                                 |
| `500` | Internal Server Error | Unhandled exception                                 |
| `503` | Service Unavailable   | External dependency down (PES Auth, Kafka, MongoDB) |