# Windows and local-model operation

Supported target: Windows 10/11 x64, Python 3.12 or 3.13, Node 24, uv, and Docker Desktop using its WSL2 Linux-container backend. Do not run the Linux MongoDB/Kafka images in Windows-container mode. Native Windows CI covers both Python versions, real process-tree cleanup, Unicode/spaced paths, and CrewAI calls to a test-only local HTTP server. This does not establish GPU performance or the capabilities of a particular downloaded model.

## Start from PowerShell

Run commands from the checkout root. Paths with spaces and Unicode are supported; no virtual-environment activation or Unix shell syntax is required.

```powershell
uv sync --locked --python 3.13
uv run python scripts/init_env.py
npm ci --prefix frontend
docker compose -f backend/docker-compose.yml up -d --wait
```

Edit `.env` before starting the application. The environment generator refuses to overwrite an existing file. In LM Studio, load the model you intend to use, start its local OpenAI-compatible server, and copy its exact served model identifier. Use this pattern:

```dotenv
OPENAI_API_KEY=lm-studio
OPENAI_MODEL_NAME=openai/<exact-model-id-from-v1-models>
LM_STUDIO_URL=http://127.0.0.1:1234/v1
LLM_MAX_OUTPUT_TOKENS=4096
CREWAI_TIMEOUT_SECONDS=600
```

Use the actual server token instead of `lm-studio` if server authentication is enabled. The `openai/` prefix selects CrewAI's OpenAI-compatible adapter; the remaining identifier must match the server. No fallback model is chosen. Configure Serper/Tavily credentials for the full research pipeline; using a local model does not remove those services' requirements.

```powershell
uv run python scripts/check_local_llm.py
uv run python scripts/check_local_llm.py --generate
uv run python scripts/bootstrap_admin.py --srn ADMIN --name Administrator
uv run python dev.py
```

The first model check only reads `/v1/models`. The explicit `--generate` check sends three small, non-sensitive capability probes for text, structured JSON, and a harmless tool call through CrewAI. It does not create users, workspaces, or sessions, start LM Studio, download models, or call a load-model endpoint. Inference may cause the externally managed server to load the selected model if its own just-in-time loading is enabled. Preload one model and configure the server's loading/concurrency policy if you want to control that behavior.

Models must support the JSON and tool-calling behavior required by the agents. A successful basic chat alone is insufficient. Prompt, tool, and completion tokens must fit the loaded context window. The former hardcoded 23,000-token Discovery completion limit is replaced by the shared configurable budget; increase it only after configuring sufficient context and memory. Hardware, drivers, model weights, quantization, context, and server configuration still need validation on the actual Windows host.

When the backend is native Windows and LM Studio is on that same host, use `127.0.0.1`. If the backend is inside a Linux container, use `http://host.docker.internal:1234/v1` and explicitly configure LM Studio networking/firewall access for that container. A container's `127.0.0.1` refers to the container. WSL networking depends on its configured mode; do not assume its loopback always reaches a Windows-host server.

## Process and record safeguards

The launcher calls Node/Vite directly, avoiding `npm.cmd` quoting issues. It refuses occupied ports and duplicate starts. The API and combined worker also have independent per-checkout OS-backed locks; readiness identifies the launch instance. A remaining lock file is not proof that a process is running: the OS lock is released on exit.

Windows children are assigned to Job Objects with kill-on-close. Descendants are terminated when their owning process closes the job or exits, including after the immediate child exits. POSIX uses owned process groups; the worker handles normal SIGTERM by canceling active jobs before closing consumers. Neither implementation kills unrelated processes by application name. The platform does not launch a second LM Studio/Ollama server.

Database uniqueness guards enforce one user per SRN and one active student workspace/session per owner, including during simultaneous first logins. Mentor workspaces have active-owner/name uniqueness guards. Existing legitimate data is not deleted to satisfy indexes: conflicting historical duplicates cause startup to fail for review. Session index v2 uses the archival timestamp rather than a changing list of pipeline states, coexists with older indexes, and protects PMF states. Application archival always sets that timestamp.

Startup and failed authentication do not seed or create dummy users/workspaces/sessions. A real authenticated student's workspace is intentionally created on first successful login. Session records are created only for explicit valid requests; a failed requested run may remain as a retryable failure with the user's inputs. That is a real attempted run, not a fabricated success. Local-model availability is checked before claiming new local-model work; a lost server after that check produces an explicit failure.

The UI has no runtime mock-data fallback. Failed comment loads show an error; uncollected Discovery alternatives/customer classifications stay unspecified. Missing export ratings are neutral. Standalone DFV, Discovery, and PMF CLIs require `--input path.json` or an explicit, clearly labeled `--sample`; examples are never silently used as real inputs.

Empty/invalid worker outputs cannot complete a stage. Quickstart rejects malformed/missing parameter assessments. PMF leaves unmeasured Sean Ellis/NPS/retention fields unknown even if a model invents numbers. These guards prevent known fabricated-data paths; they cannot prove every natural-language LLM assertion is factual. Provider outages, resource exhaustion, invalid input, and conflicting requests must surface truthful, actionable errors rather than fake results. No error-free or hallucination-free guarantee is possible.

## Verification

Run the Windows CI matrix after publishing changes, and run `check_local_llm.py --generate` on the actual Windows/model host. Integration tests use isolated MongoDB/Kafka and deterministic agent outputs; the HTTP capability test uses a test-only server. Neither is represented as a real Windows GPU/model inference test. Remaining reviewed upstream ChromaDB advisories are documented in [dependency security](dependency-security.md).
