# Historical Quickstart and PMF merge verification

This records earlier merge checks and test counts. For the current repository verification commands and behavior, see [setup and operations](workflow_and_running_guide.md) and the [repository audit](repository-audit.md).

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

## Initial dependency limitation (superseded by CI correction)

At the initial merge verification, the Python dependency audit was failing: 17 upstream advisories across ChromaDB and Filelock, including ten additional Filelock findings without reviewed exceptions. A compatible resolver dry run cannot select the required Filelock major-version fix, and the audit lists no ChromaDB fix. No findings were suppressed or newly allowlisted. See [dependency security](dependency-security.md).

Test containers use project `agis-merge-tests`, MongoDB port 27018, Kafka port 19092, and temporary databases. They do not modify the development database. The test stack is stopped after verification. No remote push is performed.

## CI failure investigation

[GitHub Actions run 41471635896](https://github.com/CIE-PESU/AGIS-2026-Experiments/actions/runs/41471635896) at commit `47c3e81` exposed six integration/browser failures. The failing API logins returned HTTP 429, and the three browser login tests consequently stayed on the login page. Module-level rate-limit windows leaked login history across independently created app instances; faster Linux runs accumulated requests before the window expired. Rate-limit windows now belong to each middleware instance. Regression tests verify that throttling still rejects excess requests and that a fresh app has independent history.

The Python 3.13 job failed only at dependency auditing; Python 3.12 was canceled by the matrix fail-fast policy. Filelock 4.2.6 now resolves its thirteen advisories through an explicit, tested uv override of LiteLLM's `<4` metadata bound. The old Filelock exceptions were removed. The audit passes with the four existing reviewed ChromaDB exceptions; no new exception was introduced.

The workflow now uses Node 24-based v7 setup/checkout actions, pins Ubuntu 24.04, and lets both Python matrix jobs finish independently. Isolated test MongoDB hostnames can be supplied through `AGIS_TEST_MONGODB_URI` for container verification.

### Follow-up verification

- Python 3.12 and 3.13: 748 unit tests passed; mypy and generated contracts passed.
- Fresh Linux container with Python 3.13, Node 24, uv 0.13.6, and locked dependencies: all workflow commands passed. This includes lint/format/types, 748 unit tests, contracts, exact requirements export, Python audit, 10 frontend tests, frontend build/audit, and all 15 real MongoDB/Kafka/browser integration tests. The runner exited with code 0. Integration tests took 74 seconds, so the complete suite also exercises the login sequence that failed in CI.
- The Python audit now succeeds while printing the four existing ChromaDB exceptions. npm audit reports zero vulnerabilities.
- The actual GitHub Actions rerun is pending publication of this follow-up commit; the original run remains a record of the old code.

The Linux verification used temporary project `agis-ci-linux` and an isolated MongoDB container, not the development database. Test containers were removed after verification. No remote push was performed.
