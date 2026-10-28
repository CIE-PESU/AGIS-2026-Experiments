# ADR 0001: Mentor persistence and workspace authentication

- Status: Amended to match current implementation, 28 October 2026.
- Decision: Keep traditional mentor records in `users` and isolated workspace identities in `workspaces`.

A traditional mentor can use a provisioned hashed-password account to supervise assigned teams. An isolated mentor-workspace identity is obtained from a high-entropy magic link and can run its own session without becoming a student or inheriting supervised-team access. These are separate supported roles; magic-link access is not the exclusive mentor authentication method.

Workspace JWT expiry follows `JWT_EXPIRY_MINUTES` (15 minutes in the new template), not a hardcoded seven-day lifetime. Magic-link workspaces have no refresh token; reopening an active link issues another access token. Revocation is checked at every protected workspace request and during SSE. Student/local-user refresh tokens use atomic rotation and preserve student workspace identity.

Mentor records remain in the existing user collection to avoid an unnecessary persistence migration. Generated `@agis.local` addresses are compatibility identities for external reviewers, not delivered email credentials. No passwords are stored in reusable seed files or shared via Fernet exports. See [RBAC](../rbac.md) and [security/migration notes](../dependency-security.md).
