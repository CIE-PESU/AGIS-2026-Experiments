# Roles and access control

Roles are issued by the backend. LocalStorage UI state cannot grant access. All protected API requests validate the JWT; mentor-workspace requests additionally validate the workspace's active/revoked status.

| Role | Session/flow access | Comments | Management |
| --- | --- | --- | --- |
| student | Create and trigger owned sessions; view owned/team sessions where supported | Read own-session feedback | None |
| mentor | View supervised-team sessions/history | Read/post on supervised teams; delete own comments | Read scoped student/team roster |
| mentor_workspace | Create/trigger/view sessions owned by its workspace | Read workspace feedback | None |
| admin | View/manage sessions through authorized admin/session operations | Read/post; delete any comment | Mentor/team/workspace lifecycle, metrics and audit |
| worker | No browser role; internal callbacks use worker-secret authentication | None | Output/failure callbacks only |

Flow idempotency never bypasses ownership. A session with no student owner is not available to an arbitrary student. Login-supplied team IDs cannot assign membership. Mentor team claims are refreshed from server-side assignments at login/refresh. Regular JWT claims remain valid until expiry; use short lifetimes and revoke/rotate credentials where needed. Workspace revocation is checked immediately on protected requests and repeatedly during SSE.

SSE requires the Authorization header in every environment. There is no unauthenticated development stream. Quickstart accepts student, mentor-workspace, and admin roles; a traditional mentor dashboard identity is not a Quickstart workspace identity.

Students and workspace guests read mentor feedback; only assigned mentors/admins write comments. The workspace UI therefore offers read-only feedback, not a reply action that the API would reject. Unauthorized resource access is hidden with 404 where the service contract requires it; role rejection uses 403. See active route dependencies and [OpenAPI](api-spec-generated.json) for exact endpoint rules.
