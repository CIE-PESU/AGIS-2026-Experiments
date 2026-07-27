 

# ADR 0001: Mentor Persistence Model & Magic Link Authentication Strategy

- **Status**: Accepted
- **Date**: 2026-07-27
- **Author**: AGIS Core Architecture Team

---

## 1. Context

The AGIS platform recently completed a major architectural shift away from traditional credential-based mentor logins toward **1:1 Isolated Mentor Workspace Magic Links**.

In this architecture:

- Mentors authenticate exclusively by opening high-entropy magic link URLs (`POST /workspace/access`), receiving a 7-day Access JWT.
- Traditional password and email credentials for mentors are deprecated.
- Each workspace is isolated to a single mentor and owns session workflows without coupling to student team structures.

As part of this shift, an architectural question arose regarding domain persistence:
*Should mentors be migrated out of the legacy `users` collection into a dedicated `mentors` MongoDB collection immediately, or should they remain persisted as `User(role="mentor")` records for the current release?*

---

## 2. Decision

1. **Retain `User(role="mentor")` in the Persistence Layer**: Mentors will remain stored as documents in the `users` collection for the current release.
2. **Exclusive Magic Link Authentication**: Mentors will authenticate exclusively via Workspace Magic Links. Traditional password-based login endpoints for mentors are deprecated.
3. **Accept Temporary Compatibility Layer**: Auto-generated fallback identity strings (`@agis.local`) are accepted as an intentional, temporary compatibility shim to satisfy the unique `User.srn` database index.
4. **Preserve ID-Based Workspace Linkage**: All workspace and team documents store explicit `mentor_id` string references (`Workspace.mentor_id`, `Team.mentor_id`), guaranteeing a clean, zero-schema-change migration path to a separate `Mentor` aggregate in the future.

---

## 3. Alternatives Considered

### Alternative A: Immediate Migration to a Dedicated `Mentor` Collection (Rejected for Current Release)

- **Description**: Immediately create a `mentors` MongoDB collection, deprecate `User(role="mentor")`, and write database migration scripts.
- **Why Rejected**:
  - High Code Churn: Requires modifying ~16 files across ODM models, repository layers, API route handlers, comment authorization logic, and test fixtures.
  - Zero Immediate End-User Benefit: Mentors currently possess only 4 domain attributes (`id`, `name`, `team_assignments`, `workspace`) and zero mentor-specific domain behaviors.
  - Delivery Risk: Introduces database migration risk during active feature iteration on core AI coaching flows (TIPS, DFV, Discovery).

### Alternative B: Poly-Typed User Model with Expanded Mentor Fields (Rejected)

- **Description**: Continuously expand the `User` document with mentor-specific attributes (bio, LinkedIn, office hours, availability).
- **Why Rejected**: Creates the "God Document" anti-pattern, polluting the IAM `User` schema with sparse fields where 80% of attributes are `null` for Students and Admins.

---

## 4. Consequences

### Positive Consequences

- **High Engineering Velocity**: Avoids a multi-file refactoring sprint, allowing focus to remain on core coaching workflows.
- **Zero Database Migration Risk**: Avoids mutating live production documents.
- **100% Backward Compatibility**: Fully preserves existing team allocation queries and API response contracts.
- **Preserved Migration Path**: Because `Workspace.mentor_id` and `Team.mentor_id` store explicit IDs, transitioning to a separate collection in the future requires zero schema changes on dependent models.

### Negative Consequences & Accepted Technical Debt

- **Domain-Persistence Mismatch**: Mentors remain persisted in the IAM `users` collection despite not using IAM password credentials.
- **Placeholder Identity Fields**: Auto-generated fallback emails (`f"{name}_{uuid}@agis.local"`) remain in the database to satisfy the `User.srn` unique B-tree index.
- **Dead Code**: Legacy password-login handling branches in `auth_service.py` remain dormant for backward compatibility.

---

## 5. Migration Triggers (Phase 2 Transition Criteria)

This ADR mandates a transition to a dedicated `Mentor` aggregate root (`mentors` MongoDB collection) **when at least two of the following quantitative, objective triggers are met**:

1. **Domain Attribute Density ($\ge 3$ Mentor-Only Attributes)**: The product roadmap introduces mentor bio descriptions, LinkedIn URLs, profile photos, expertise tags, or professional titles.
2. **Mentor-Owned Business Rules**: Addition of mentorship scheduling, office hours management, availability calendars, or meeting history logs.
3. **External Industry Mentors**: Requirement to invite third-party guest mentors who undergo an external onboarding workflow without institutional credentials.
4. **Dedicated Mentor Subdomain Autonomy**: Requirement for independent mentor analytics, feedback rating engines, or mentor activity tracking.

### 5.1 Anti-Enum-Creep Policy

This Phase 1 architecture intentionally supports **exactly two advisor types**:

- **Faculty Mentor**
- **External Reviewer**

Future participant categories (for example Investors, Judges, Coaches, Alumni Mentors, Grant Reviewers, etc.) **must not be added by extending the `AdvisorType` enumeration**.

The introduction of additional participant categories indicates that AGIS has reached the product maturity threshold for the planned **People → Roles → Capabilities** architecture.

At that point:

1. Replace the `Advisor` model with a `Person` model.
2. Introduce role assignments (`Person.roles`).
3. Preserve `Workspace` as an access capability.

This ADR intentionally defines this migration trigger to prevent gradual, unchecked enum expansion.

---

## 6. Future Evolution

> **Notice**: This ADR is explicitly expected to be **superseded by ADR 0002** (*"Introduction of Dedicated Mentor Aggregate Root"*) once the migration triggers in Section 5 are met.

---

## 7. References

- [docs/backend-arch.md](<file:///Users/saicharanbk/Documents/Github%20Projects/AGIS-2026-Experiments/docs/backend-arch.md>) — AGIS Backend System Architecture & Layering.
- [docs/rbac.md](<file:///Users/saicharanbk/Documents/Github%20Projects/AGIS-2026-Experiments/docs/rbac.md>) — Role-Based Access Control Specification.
- [docs/user-journey.md](<file:///Users/saicharanbk/Documents/Github%20Projects/AGIS-2026-Experiments/docs/user-journey.md>) — Workspace Magic Link Access & Redemption Journey.
