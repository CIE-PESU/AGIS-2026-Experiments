# Product concept and implementation alignment

Reviewed on 4 November 2026. This review uses the repository's user journey, role policy, flow schemas, and agent rubrics as the product contract. It does not certify live provider availability or replace testing on another machine.

| Product concept | Implemented behavior | Evidence |
| --- | --- | --- |
| Roles have different jobs | Students evaluate ideas; mentors supervise assigned teams; admins manage accounts, teams, and workspace links | Auth validators, role dependencies, session ownership checks, and shared-login tests |
| Optional rapid evaluation | Quickstart returns ten ratings independently of persisted pipeline progress; available to students and isolated workspace guests | Quickstart route and page guards, independent saved-state storage, stage mapping tests |
| Full founder evaluation | Seven-field intake starts PreEval, validation/regulatory research, Ethics, and TIPSC | Session creation schema, asynchronous executor, agent runtime tests |
| Founder clarification | Server owns the pending question and supports at most three follow-up turns | Executor follow-up loop and regression tests |
| Progression follows evidence | TIPSC's `ready_for_dfv` unlocks DFV; an explicit DFV GO unlocks Discovery; completed Discovery output unlocks PMF | Flow service/repository guards and frontend stage tests |
| Completion differs from success | A completed TIPSC evaluation can contain yellow/red ratings; DFV NO-GO is a completed assessment that permits revision | Canonical progress helper and dashboard statistics tests |
| Discovery prepares research | Discovery generates a customer interview/discovery plan; generating a plan does not mean interviews have been conducted | Discovery payload and agent report contract |
| PMF assesses supplied material | PMF uses founder inputs and upstream reports for a qualitative assessment; no measured survey or cohort input is implemented | PMF job schema, agent output normalization, evidence tests, and PMF page |
| Mentors can see real progress | Team views use canonical IMPORTANT scores and completed output records, not the existence of queued/failed records | Team-progress endpoint and concept-alignment regressions |
| Reports survive later stages | Prior reports remain available during PMF runs/retries; exports include saved PMF output | Flow claims, PMF tests, and report exporter |
| Finished work can be archived | Idle Discovery-completed and PMF-completed/failed sessions can be archived; running work cannot | Session service/repository and state-transition tests |
| Fresh clones get shared logins | Startup provisions nine accounts with hashes; metadata import order does not prevent credential provisioning | Isolated MongoDB checks and provisioning regressions |

## Corrections from this review

- Kept Quickstart available independently instead of marking it complete when TIPSC completes.
- Required an explicit DFV GO for the Discovery entry point and saved Discovery output for initial PMF access.
- Made dashboard completion counts independent of positive ratings and stopped counting running/failed DFV jobs as completed.
- Corrected the team-progress importance field and removed positive defaults for missing TIPS scores.
- Stopped treating unfinished Discovery records as completed work.
- Added Discovery completion to the legal archive transitions and clarified its UI label: the historical backend state `completed` means Discovery finished, with optional PMF next.
- Updated setup and role documentation to match the branch's shared logins and Quickstart access.

## Product boundaries

The application provides AI assessments and research plans. It does not conduct customer interviews, collect structured Sean Ellis/NPS survey responses, ingest retention cohorts, or establish measured product-market fit. PMF numerical scores, when present, are qualitative. Adding measured customer validation would require a separate evidence-collection feature across the UI, API, persistence, and agent inputs.

Live LLM/search/PES behavior and real Kafka/browser integration still require their respective environments. Automated substitute outputs establish application behavior, not the accuracy of business conclusions.

## Shared-account browser verification

`tests/frontend/test_shared_roles.py` signs into all nine bundled accounts through the real login form against an isolated MongoDB database. It checks dashboard content, mentor roster isolation, role-specific navigation, prohibited page redirects, API role rejection, session restoration, and logout. It does not invoke evaluation agents. The CI integration job enables this test alongside the existing pipeline/browser tests.

To run only these checks with a local MongoDB instance and Playwright Chromium installed:

```bash
AGIS_AUTH_BROWSER=1 AGIS_TEST_MONGODB_URI=mongodb://127.0.0.1:27017 .venv/bin/pytest tests/frontend/test_shared_roles.py -q
```

The test creates and deletes its own database; it does not change development users or team assignments.
