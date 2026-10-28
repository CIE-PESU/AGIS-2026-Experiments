# DFV agent

CrewAI analysis of Desirability, Feasibility, and Viability. The platform invokes `main.py::run_analysis` through the combined worker's isolated agent subprocess.

Install the root locked environment with `uv sync --locked`; see [platform setup](../docs/workflow_and_running_guide.md). Configure the root LLM endpoint/model/key and Serper key as described in [model configuration](../docs/model-config.md). The worker uses `backend/models/schema.py` as its Kafka contract and posts accepted output to the internal backend API. It does not write session state directly.

A NO-GO result allows revised DFV input and blocks Discovery. See [flow shapes](../docs/flow-shapes.md) and [worker operations](docs/dfv-worker-runbook.md). Notebook experiments are reference material, not the platform entry point.
