# API specification

The versioned API base is `/api/v1`. The generated [OpenAPI document](api-spec-generated.json) is the executable source of truth for mounted routes, parameters, request schemas, and declared responses. Development Swagger is at `/docs`; production disables Swagger/Redoc. Regenerate with `uv run python backend/scripts/export_openapi.py` and check with `uv run python scripts/check_contracts.py`.

Protected endpoints use `Authorization: Bearer <access_token>`. Workspace tokens are checked for revocation. Worker callbacks use `X-Worker-Secret` under `/internal`; the worker secret is never sent to browser clients.

## Main routes

| Operation | Route | Behavior |
| --- | --- | --- |
| Login | `POST /auth/login` | PES authentication or provisioned local hashed-password account |
| Refresh | `POST /auth/refresh` | Atomically consume opaque token, issue new token pair, preserve student workspace |
| Logout | `POST /auth/logout` | Revoke refresh token; access token expires at configured expiry |
| Current identity | `GET /auth/me` | User profile or validated workspace identity |
| Create session | `POST /sessions` | Seven-field founder intake; owner-scoped Idempotency-Key required; starts TIPSC |
| Session detail/list | `GET /sessions/{session_id}`, `GET /sessions` | Role/ownership filtering |
| Active session | `GET /sessions/user/{student_id}/session` | Active student/workspace session |
| Archive/delete | `DELETE /sessions/{session_id}`, `DELETE /sessions/{session_id}/permanent` | Server enforces allowed lifecycle and ownership |
| Retry TIPSC | `POST /sessions/{session_id}/trigger/tipsc` | Starts a retryable TIPSC run |
| Founder answer | `POST /sessions/{session_id}/followup` | Claims one pending turn atomically; schedules reevaluation |
| DFV | `POST /sessions/{session_id}/trigger/dfv` | Requires TIPSC readiness, publishes validated job |
| Discovery | `POST /sessions/{session_id}/trigger/discovery` | Rejects DFV NO-GO; publishes validated job |
| Stream | `GET /sessions/{session_id}/stream` | Authenticated SSE, no URL tokens; expires/rechecks authorization |
| Comments | `GET/POST /sessions/{session_id}/comments` | Raw list/object responses; only assigned mentors/admins can post |
| Delete comment | `DELETE /comments/{comment_id}` | Author/admin permission; 204 response |
| History | `GET /sessions/{session_id}/history` | Authorized audit history |
| Mentor views | `/mentor/...` | Supervised sessions and teams |
| Admin management | `/admin/...` | Mentors, students, teams, metrics, audit, isolated workspaces |
| Magic-link redemption | `POST /workspace/access` | Public high-entropy-token exchange for workspace access token |
| Quickstart | `POST /quickstart/evaluate` | Authenticated 10-parameter evaluation; independent of persisted session pipeline |
| Probes | `GET /health`, `/ready`, `/live` | All under `/api/v1`; public, rate-limit exempt |

Flow triggers accept optional `Idempotency-Key`. Replay is session/owner/flow scoped and body-checked; it returns the original run response. A reused key with a changed body returns 409. Responses must not be interpreted as a newly started run merely because the HTTP status is 202.

Successful session/auth/flow operations use `{data, meta}`; paginated operations add `pagination`. Some existing admin mutations return messages and admin-specific data. Comments deliberately return raw objects/arrays. The shared frontend client handles both contracts explicitly. Errors use `{error: {code, message, field, request_id, timestamp}}`; clients must check HTTP status rather than looking for an `error` field in a 200 response. Login, schema, ownership, concurrency, dependency-outage, and body-limit failures use appropriate 4xx/5xx statuses.

## Internal callbacks

`POST /internal/sessions/{session_id}/output` accepts `correlation_id`, `flow`, `output`, `duration_seconds`, and `worker_id`. `POST .../failure` accepts `correlation_id`, `flow`, `error_code`, `error_message`, and `retry_count`. Both require the worker header. Duplicate accepted results/failures are safe to replay. A stale run is rejected; a version conflict is retryable. The worker persists callbacks before delivery and retains offsets during transient outages.

See [flow shapes](flow-shapes.md), [RBAC](rbac.md), and the generated schemas for field constraints.
