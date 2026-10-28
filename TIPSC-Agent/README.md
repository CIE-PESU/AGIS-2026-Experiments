# TIPSC agent

The platform's asynchronous assessment pipeline performs PreEval, concurrent validation/regulatory research, Ethics screening, compliance context, TIPSC scoring, and up to three founder follow-ups. It parks pending questions in MongoDB rather than waiting for terminal input.

Install and run through the root [platform setup](../docs/workflow_and_running_guide.md). The API initializes `src/engine/async_pipeline_executor.py` and uses `src/engine/db.py` for version/run-guarded persistence. Agent schemas have the distinct module name `src/tipsc_models.py` to avoid shadowing backend persistence models. Prompts are in `src/config/` and rubrics in `src/skills/`.

The standalone `src/main.py` and synchronous pipeline are interactive experiments. They are not used by the API and must not be run against platform session records. Configure shared providers through the root environment; see [models](../docs/model-config.md). The root lockfile is the tested platform dependency contract.
