# User journey

1. Open the landing page and sign in. Student credentials use PES authentication; local mentor/admin passwords must be provisioned. A magic link creates an isolated mentor-workspace identity.
2. Optionally use Quickstart for a rapid ten-parameter evaluation. Quickstart returns a result without creating or automatically progressing a persisted session.
3. Submit the seven-field founder intake in the workspace. The backend creates one active session and starts PreEval, validation/regulatory research, Ethics, then TIPSC.
4. If Ethics rejects the idea, review the reason. If TIPSC needs evidence, answer the pending founder question; up to three turns are supported. The backend owns the current question and stage state.
5. When TIPSC allows DFV, submit Desirability, Feasibility, and Viability context. Kafka dispatches the analysis; the workspace shows progress and the resulting decision.
6. A NO-GO decision permits revising DFV inputs and retrying. A passing decision allows Customer Discovery, where the founder supplies customer/assumption context and receives an interview plan.
7. Polling or authenticated streaming updates the UI. Dependency errors and timeouts appear as retryable failures rather than permanently running jobs. Repeating a trigger with the same idempotency key replays its original response; changed input requires a new key.
8. Read feedback from assigned mentors. Student/workspace feedback is read-only; mentors add comments from their dashboard. Admins manage teams, mentors, and isolated workspace links.
9. Archive a finished/retryable session before starting another. Revoked workspace links stop granting access immediately; associated application data is removed asynchronously while audit records remain.

See [roles](rbac.md), [flow inputs](flow-shapes.md), and [setup](workflow_and_running_guide.md).
