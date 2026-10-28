# AGIS — Setup, Workflow & Running Guide

> **Fresh clone? Start here.** This is the single source of truth for getting
> the full AGIS platform running locally after pulling the repo.

---

## 1. System Prerequisites

| Tool                    | Version   | Notes                                     |
| ----------------------- | --------- | ----------------------------------------- |
| Python                  | `3.12+` | Check: `python3 --version`              |
| Node.js & npm           | `18+`   | Check: `node --version`                 |
| Docker & Docker Compose | Latest    | Must be running                           |
| LLM Server              | —        | LM Studio / Ollama / NVIDIA NIM (see §3) |

---

## 2. First-Time Setup

All commands run from the **project root** unless stated otherwise.

### Step 1 — Clone & enter repo

```bash
git clone <repo-url>
cd AGIS-2026-Experiments
```

### Step 2 — Create a single root virtual environment

> **Changed**: there is now **one** shared `requirements.txt` at the project
> root. You no longer need separate venvs per submodule.

```bash
# Create venv (only once)
python3 -m venv .venv

# Activate it (do this in EVERY terminal you open for Python)
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\Activate.ps1        # Windows PowerShell
```

### Step 3 — Install all Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4 — Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### Step 5 — Configure environment variables

The repo ships a fully documented template at the root:

```bash
cp .env.example .env
```

Then open `.env` and fill in **at minimum** these values:

```env
# --- Auth (generate any 32+ char random string) ---
JWT_SECRET=CHANGE_ME_TO_A_LONG_RANDOM_SECRET_AT_LEAST_32_CHARACTERS
WORKER_INTERNAL_SECRET=CHANGE_ME_TO_A_LONG_RANDOM_WORKER_SECRET

# --- LLM (choose one block) ---

# Option A: NVIDIA NIM (default)
OPENAI_API_KEY=YOUR_NVIDIA_API_KEY
OPENAI_MODEL_NAME=openai/nvidia/nemotron-3-ultra-550b-a55b
LM_STUDIO_URL=https://integrate.api.nvidia.com/v1

# Option B: Local LM Studio
# OPENAI_API_KEY=lm-studio
# OPENAI_MODEL_NAME=openai/qwen/qwen3.5-9b
# LM_STUDIO_URL=http://localhost:1234/v1

# --- Search APIs (at least one required for agents) ---
SERPER_API_KEY=YOUR_SERPER_API_KEY
TAVILY_API_KEY=YOUR_TAVILY_API_KEY
```

Everything else in `.env` has sensible defaults for local development.

---

## 3. Infrastructure — Start Docker Services

The `docker-compose.yml` lives in `backend/`. It starts **Kafka** (KRaft mode,
no Zookeeper) and optionally MongoDB if you add it.

```bash
# From project root
docker compose -f backend/docker-compose.yml up -d
```

If the worker prints `Unable to bootstrap from [('localhost', 9092)]`, Kafka is
not reachable. Run the command above, then check
`docker compose -f backend/docker-compose.yml ps` before restarting the app.
The backend `/ready` endpoint returns 503 while Kafka is unavailable.

> **Note**: MongoDB is **not** in the compose file — the app connects to
> `mongodb://localhost:27017` by default. Install MongoDB locally or add a
> `mongo` service to the compose file if needed.

### Services started

| Service         | Port      | URI                           |
| --------------- | --------- | ----------------------------- |
| Kafka (KRaft)   | `9092`  | `localhost:9092`            |
| MongoDB (local) | `27017` | `mongodb://localhost:27017` |

To stop:

```bash
docker compose -f backend/docker-compose.yml down
```

---

## 4. Running the Platform

From the project root, start the backend, combined DFV/Discovery/PMF worker,
notification worker, and frontend together:

```bash
source .venv/bin/activate
python dev.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` and then run
`python dev.py`. Use `Copy-Item .env.example .env` in place of the `cp` command
in Step 5.

Open **http://localhost:5176**. The backend runs at **http://localhost:8004**
(`http://localhost:8004/ready` checks startup readiness). The launcher starts
services in this order, waiting for each one to become ready before starting
the next:

1. Backend (`:8004/ready`)
2. Notification worker (Kafka consumer and MongoDB ready)
3. Combined DFV/Discovery/PMF worker (Kafka consumers and producer started)
4. Frontend (`:5176`)

The services keep running together; “ready” is the startup gate, not process
exit. `AGIS ready` prints only after step 4 succeeds.
Press **Ctrl+C** to stop the services it started. Kafka and MongoDB must already
be running as described in §3; `dev.py` does not start Docker services.

If you use a local LLM, start its server before `python dev.py`. With NVIDIA
NIM/cloud, ensure the API key and model settings are present in `.env`.

The notification worker starts with `dev.py`. The frontend currently reads
session status directly from the backend, so its progress display also works
when no notification events have been published.

### Run services separately

Use the commands below when debugging an individual service. Start Kafka and
MongoDB first, then the backend, notification worker, combined agent worker,
and frontend. Activate
the root `.venv` in each Python terminal.

---

### Terminal 1 — LLM Server

**Option A — Local LM Studio**

1. Open LM Studio → load a model (e.g. `qwen3.5-9b`)
2. Start the local server → it listens on `http://127.0.0.1:1234/v1`

**Option B — NVIDIA NIM / cloud**

- Nothing to start locally; just ensure `OPENAI_API_KEY` is set in `.env`

---

### Terminal 2 — FastAPI Backend

```bash
source .venv/bin/activate
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8004
```

- API docs: **http://localhost:8004/docs**
- Health check: **http://localhost:8004/health**

---

### Terminal 3 — Notification Worker

```bash
source .venv/bin/activate
cd backend
python -m workers.notification_worker
```

---

### Terminal 4 — Combined Agent Worker (DFV + Discovery + PMF)

```bash
source .venv/bin/activate
cd backend
python -m workers.combined_agent_worker
```

Consumes from Kafka topics:

- `userSession.dfv`
- `userSession.discovery`
- `userSession.pmf`

---

### Terminal 5 — React Frontend

```bash
cd frontend
npm run dev
```

- Web app: **http://localhost:5176**

Use port **5176** for this branch. An older browser tab at `localhost:5174`
may show stale frontend code; close it and open the address above.

---

## 5. One-Time Database Migration

Only needed if you have pre-existing data from an older schema:

```bash
source .venv/bin/activate
python backend/scripts/migrate_session_teams.py
```

---

## 6. Verification & Testing

### Run unit tests

```bash
source .venv/bin/activate
pytest tests/
```

### Run API smoke tests (requires backend running)

```bash
source .venv/bin/activate
python backend/scripts/smoke_test.py
python backend/scripts/test_api_comments.py
```

### Check DB state

```bash
source .venv/bin/activate
python backend/scripts/check_db.py
```

---

## 7. System Architecture

```
User Browser (React :5176)
        │
        ▼  HTTP REST / JWT
FastAPI Backend (:8004) ──────────────► MongoDB (:27017)
        ├── TIPSC pipeline (in process) ────┘
        │
        ▼  Kafka Events
  Kafka (:9092)
    • userSession.dfv
    • userSession.discovery
    • userSession.pmf
        │
        ▼  Kafka Consumers
  Background Workers ──► Backend internal API ──► MongoDB
    • combined_agent_worker.py
    • notification_worker.py
        │
        ▼  OpenAI-compatible API
  LLM Server (LM Studio / NVIDIA NIM)
```

### Request flow

1. **Session Created** → Frontend → Backend writes to MongoDB (`status: queued`) and starts TIPSC in process.
2. **TIPSC Evaluation** → TIPSC runs against the LLM and updates the session → `tipsc_completed` or a founder follow-up.
3. **DFV Evaluation** → Student triggers DFV → Backend emits `userSession.dfv` → `combined_agent_worker` evaluates Desirability / Feasibility / Viability → `dfv_completed`
4. **Customer Discovery** → Student triggers Discovery → Backend emits `userSession.discovery` → Worker generates JTBD interview guide → `completed`.
5. **PMF** → Student triggers PMF → Backend emits `userSession.pmf` → Worker evaluates available evidence → `pmf_completed`.
6. **Updates** → Frontend polls `GET /api/v1/sessions/{id}` to show progress.

---

## 8. Quick-Reference Cheat Sheet

```bash
# === ONCE (fresh clone) ===
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env
cd frontend && npm install && cd ..

# === EVERY SESSION (from project root) ===
docker compose -f backend/docker-compose.yml up -d
source .venv/bin/activate
python dev.py                         # backend :8004, both workers, frontend :5176

```

---

## 9. Troubleshooting

| Symptom                              | Fix                                                                                                        |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError`              | Make sure venv is activated: `source .venv/bin/activate`                                                 |
| `Connection refused` on port 9092  | `docker compose -f backend/docker-compose.yml up -d`                                                     |
| `Connection refused` on port 27017 | Start MongoDB locally or add it to docker-compose                                                          |
| LLM agent times out                  | Verify your LLM server is running and `LM_STUDIO_URL` / `OPENAI_API_KEY` are set correctly in `.env` |
| `JWT_SECRET` error on startup      | Ensure `.env` has a 32+ character `JWT_SECRET` value                                                   |
| Frontend can't reach backend         | Check `CORS_ALLOWED_ORIGINS=http://localhost:5176` is in `.env`                                        |
