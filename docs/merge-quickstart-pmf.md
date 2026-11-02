# Quickstart and PMF merge verification

Verified on 2 November 2026 on `develop-merge_q_p`.

Sources: `develop-quickstart` at `176ae9d` and `develop-pmf` at `1cdc5dd`. Merge commit: `b2d8ac9`. Follow-up integration repairs connect PMF to the existing Quickstart architecture.

## Preserved behavior

- Quickstart agent, evaluation API, page, saved drafts/results, branding, themes, authentication, owner isolation, and session management.
- TIPSC evaluation, Ethics/regulatory checks, founder follow-up, DFV decisions/revision, and customer-discovery reports.
- PMF agent and page, Sean Ellis/NPS/retention evidence handling, customer alignment, demand, value proposition, defensibility, strengths, and risks.
- Version/run guards, atomic flow claims, scoped idempotency, persistent worker callbacks, dead letters, agent timeout/cancellation, and retry recovery now also cover PMF.
- Retry forms retain saved answers, failure details are exposed, and full session exports include PMF.

The Quickstart agent/API/page and PMF agent/page match their respective source branch implementations. Generated OpenAPI and database schemas include PMF.

## Repairs

Added PMF route/adaptor mapping, job and result schemas, persistence, transitions, worker consumer/subprocess routing, output/failure callbacks, timeout recovery, stage mapping, dashboard entry, and exports. Retained Quickstart's newer dependency/authentication architecture while resolving conflicts. Removed duplicate shutdown/logger code, prevented notification field injection, stopped DFV credential logging, fixed empty-response retries, and terminate agent process groups on timeout/cancellation. Generated runtime credentials, readiness markers, bytecode, and build output are excluded from the merged source.

## Verification

- 744 Python tests passed without external infrastructure.
- 15 integration/browser tests passed using isolated real MongoDB and Kafka, including real application startup, login/refresh/logout, Quickstart API contracts, founder follow-up, DFV/Discovery, PMF retries, ownership, idempotency, durable delivery, stale callback rejection, archive, and browser reload restoration.
- 10 frontend tests passed, including Quickstart persistence, authentication refresh, polling, and PMF stage access.
- Backend Ruff lint/format and mypy passed; frontend TypeScript and production build passed using freshly installed locked dependencies.
- Generated contract checks, agent Python compilation, and Git whitespace checks passed.
- npm audit: zero vulnerabilities.

Automated model outputs are deterministic substitutes; these checks do not validate live LLM/search/PES-provider availability or establish that every possible runtime bug is absent.

## Remaining dependency limitation

The Python dependency audit remains failing: 17 upstream advisories across ChromaDB and Filelock, including ten additional Filelock findings without reviewed exceptions. A compatible resolver dry run cannot select the required Filelock major-version fix, and the audit lists no ChromaDB fix. No findings were suppressed or newly allowlisted. See [dependency security](dependency-security.md).

Test containers use project `agis-merge-tests`, MongoDB port 27018, Kafka port 19092, and temporary databases. They do not modify the development database. The test stack is stopped after verification. No remote push is performed.
