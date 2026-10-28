# Quickstart evaluation

Quickstart combines three Ethics gates, four TIPSC dimensions, and three DFV pillars into ten GREEN/YELLOW/RED ratings with reasons and advice. It is independent of the persisted TIPSC → DFV → Discovery session pipeline.

`POST /api/v1/quickstart/evaluate` requires a student, mentor-workspace, or admin JWT. Supply `problem`, `customer`, `solution`, `consequence`, `business_model`, `urgency`, and `hurdles`. The result includes the input, ten parameter ratings, red/yellow/green counts, per-parameter advice, priority advice, and timestamp. See [generated OpenAPI](api-spec-generated.json) for validation constraints.

The route invokes `quickstart-agent/quickstart_agent/main.py::run_quickstart_eval_async`. Models are in that package's `models.py`, prompts in `config/`, and the rubric in `skills/QUICKSTART_SKILL.md`. Configuration comes from the root environment and [model configuration](model-config.md). The API loader adds the agent directory to the import path; callers should use the platform endpoint instead of maintaining a second environment.

Quickstart does not need the combined Kafka worker for its evaluation. The complete platform readiness check still expects configured infrastructure and TIPSC initialization. Ordinary CI uses deterministic agent outputs; validate provider-specific model behavior separately with non-sensitive input. Do not treat Quickstart ratings as proof that a business, legal, or regulatory decision is correct.
