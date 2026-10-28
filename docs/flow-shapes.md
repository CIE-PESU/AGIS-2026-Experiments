# Flow shapes

Canonical input schemas live in `backend/schemas`; Kafka job shapes live in `backend/models/schema.py`. See [generated OpenAPI](api-spec-generated.json) and [persisted session schema](schema.json). All public paths below have the `/api/v1` prefix.

## Founder intake

`POST /sessions` requires an Idempotency-Key and these fields:

```json
{
  "problem_statement": "A sufficiently detailed description of the customer problem.",
  "customer_segment": "A sufficiently detailed description of the target customers.",
  "consequence": "A sufficiently detailed description of the impact if unsolved.",
  "assumptions": ["The customer will pay for a better alternative"],
  "proposed_solution": "A sufficiently detailed description of the proposed solution.",
  "target_geography": "India",
  "industry_sector": "Education"
}
```

Field limits are enforced by `SessionCreateRequest`. The intake is persisted as `preeval_input`; `idea` is the compatibility representation of `proposed_solution`. IDs are MongoDB ObjectId strings, not prefixed synthetic session IDs.

## TIPSC and follow-up

TIPSC persists `preeval`, `validation`, `regulatory`, `ethics`, `compliance_context`, and `tipsc`. The output includes refined idea, solution alignment, TIPS scores/reasons, readiness, `ready_for_dfv`, and follow-up metadata. Agent schemas are in `TIPSC-Agent/src/tipsc_models.py`; backend persistence accepts `I`/`I_reason` as aliases of `IMPORTANT`/`IMPORTANT_reason`.

When status is `waiting_for_founder`, submit `{"answer": "Founder evidence and explanation"}` to `/sessions/{id}/followup`. The response accepts one turn for asynchronous reevaluation. Up to three follow-up turns are supported; clients must use the server's pending question/status.

## DFV

`POST /sessions/{id}/trigger/dfv` accepts three strings of 100–3000 characters:

```json
{
  "desirability_context": "Customer evidence, unmet needs, alternatives, and research...",
  "feasibility_context": "Technical capabilities, constraints, resources, and execution plan...",
  "viability_context": "Revenue, pricing, costs, competition, and commercial assumptions..."
}
```

The Kafka envelope contains `userSession_id`, `idea_name`, `correlation_id`, `retry_count`, `published_at`, and nested `payload`. Worker output is stored under `dfv` with status/timing/correlation metadata and its structured `output`. The decision is read from `output.decision` or `output.final_decision.status`. NO-GO permits a revised DFV attempt; it blocks Discovery.

## Discovery

The API and Kafka use the same `DiscoveryJobPayload`: `target_customer_segment` (segment/role/customer_type objects), `problem_statement`, `problem_consequence`, `current_alternatives`, `key_assumptions`, `what_we_already_know`, `biggest_uncertainty`, `customer_type`, and `proposed_solution_context` (`purpose`, `summary`). List fields are JSON arrays. The worker wraps the generated report as `discovery.output.report` with status and timing metadata. Accepted Discovery output moves the session to `completed`.

Transport envelopes are described in [API specification](api-spec.md). Never duplicate worker payload definitions in frontend or agent code without validating against these schemas.
