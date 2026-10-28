# Model configuration

The root `.env` supplies `OPENAI_MODEL_NAME`, `LM_STUDIO_URL` (an OpenAI-compatible `/v1` endpoint), and `OPENAI_API_KEY`. TIPSC, DFV, Discovery, and Quickstart read this shared configuration. Never commit keys. Exact CrewAI, tools, and LiteLLM versions are resolved together by the root lockfile; the LiteLLM dependency is explicit rather than CrewAI's optional pinned extra.

The template uses NVIDIA NIM:

```dotenv
OPENAI_MODEL_NAME=openai/nvidia/nemotron-3.5-lightning-30b-a3b
LM_STUDIO_URL=https://integrate.api.nvidia.com/v1
OPENAI_API_KEY=YOUR_NVIDIA_NIM_API_KEY
```

For local LM Studio, set the model identifier to the model actually served and use `http://127.0.0.1:1234/v1`. Model availability is provider-dependent; template names are examples, not guaranteed entitlements. Keep the provider prefix required by CrewAI/LiteLLM. The agents omit reasoning for the specifically configured lightning model; other models use their provider defaults.

Search-enabled agents use `TAVILY_API_KEY` and/or `SERPER_API_KEY`. Configure both for the complete pipeline. LLM and search service outages are independent of MongoDB/Kafka readiness. A ready API does not prove provider credentials are valid.

`AGENT_TIMEOUT_SECONDS` limits the combined worker's agent subprocess. TIPSC uses stage-level validation/regulatory timeouts where configured and the timeout supervisor for abandoned pipeline work. Review provider limits and total pipeline duration before changing these values. A subprocess timeout stops the local process; it cannot guarantee a remote provider cancels billing for a request already accepted.

Automated integration tests use controlled agent outputs and never call these providers. A live provider check must use non-sensitive sample input and be run separately from ordinary CI.
