# Customer discovery planner

A CrewAI agent that creates a Jobs-To-Be-Done customer interview plan from target segments, problem/consequences, alternatives, assumptions, known evidence, uncertainties, and proposed-solution context.

The platform invokes `main.py::run_discovery_analysis` through the combined worker's isolated subprocess after DFV passes. Its Kafka payload uses the canonical `DiscoveryJobPayload` in `backend/models/schema.py`; the report is returned through the backend callback and stored in `discovery.output.report`.

Use the root locked environment and [platform setup](../docs/workflow_and_running_guide.md). Models are configurable OpenAI-compatible providers, not restricted to Bonsai/local hosting. See [model configuration](../docs/model-config.md). `customer_interview_planner.py` contains agent construction and JTBD skills live in `skills/`. The Kafka helper scripts are experimental utilities; use the platform worker for normal operation.
