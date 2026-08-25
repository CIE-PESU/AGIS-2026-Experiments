# AGIS — Setup, Workflow & Running Guide

> **Fresh clone? Start here.** This is the single source of truth for getting
> the full AGIS platform running locally after pulling the repo.

---

## 1. System Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | `3.12+` | Check: `python3 --version` |
| Node.js & npm | `18+` | Check: `node --version` |
| Docker & Docker Compose | Latest | Must be running |
| LLM Server | — | LM Studio / Ollama / NVIDIA NIM (see §3) |

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
# .venv\Scripts\activate           # Windows
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

> **Note**: MongoDB is **not** in the compose file — the app connects to
> `mongodb://localhost:27017` by default. Install MongoDB locally or add a
> `mongo` service to the compose file if needed.

### Services started

| Service | Port | URI |
|---|---|---|
| Kafka (KRaft) | `9092` | `localhost:9092` |
| MongoDB (local) | `27017` | `mongodb://localhost:27017` |

To stop:
```bash
docker compose -f backend/docker-compose.yml down
```

---

## 4. Running the Platform

Open **5 terminal windows**, each with the venv activated:

```bash
# In each terminal:
source .venv/bin/activate
```

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
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: **http://localhost:8000/docs**
- Health check: **http://localhost:8000/health**

---

### Terminal 3 — Combined Agent Worker (DFV + Discovery)

```bash
source .venv/bin/activate
cd backend
python -m workers.combined_agent_worker
```

Consumes from Kafka topics:
- `userSession.dfv`
- `userSession.discovery`

---

### Terminal 4 — Notification Worker

```bash
source .venv/bin/activate
cd backend
python -m workers.notification_worker
```

---

### Terminal 5 — React Frontend

```bash
cd frontend
npm run dev
```

- Web app: **http://localhost:5173**

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
User Browser (React :5173)
        │
        ▼  HTTP REST / JWT
FastAPI Backend (:8000) ──────────────► MongoDB (:27017)
        │                                    ▲
        ▼  Kafka Events                      │
  Kafka (:9092) ──────────────────────────── ┤
    • userSession.tipsc                      │
    • userSession.dfv                        │
    • userSession.discovery                  │
        │                                    │
        ▼  Kafka Consumers                   │
  Background Workers ─────────────────────── ┘
    • combined_agent_worker.py
    • notification_worker.py
        │
        ▼  OpenAI-compatible API
  LLM Server (LM Studio / NVIDIA NIM)
```

### Request flow

1. **Session Created** → Frontend → Backend writes to MongoDB (`status: queued`) → emits `userSession.tipsc`
2. **TIPSC Evaluation** → `TIPSC-Agent` picks up event, runs CrewAI crew against LLM, updates session → `tipsc_completed`
3. **DFV Evaluation** → Student triggers DFV → Backend emits `userSession.dfv` → `combined_agent_worker` evaluates Desirability / Feasibility / Viability → `dfv_completed`
4. **Customer Discovery** → Student triggers Discovery → Backend emits `userSession.discovery` → Worker generates JTBD interview guide → `completed`
5. **Real-time Updates** → Frontend polls `GET /api/v1/sessions/{id}` to show live progress

---

## 8. Quick-Reference Cheat Sheet

```bash
# === ONCE (fresh clone) ===
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env
cd frontend && npm install && cd ..

# === EVERY SESSION ===
docker compose -f backend/docker-compose.yml up -d   # T0: infra
source .venv/bin/activate && cd backend && uvicorn main:app --reload --port 8000   # T2: API
source .venv/bin/activate && cd backend && python -m workers.combined_agent_worker # T3: DFV worker
source .venv/bin/activate && cd backend && python -m workers.notification_worker   # T4: notifs
cd frontend && npm run dev                                                           # T5: UI
```

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | Make sure venv is activated: `source .venv/bin/activate` |
| `Connection refused` on port 9092 | `docker compose -f backend/docker-compose.yml up -d` |
| `Connection refused` on port 27017 | Start MongoDB locally or add it to docker-compose |
| LLM agent times out | Verify your LLM server is running and `LM_STUDIO_URL` / `OPENAI_API_KEY` are set correctly in `.env` |
| `JWT_SECRET` error on startup | Ensure `.env` has a 32+ character `JWT_SECRET` value |
| Frontend can't reach backend | Check `CORS_ALLOWED_ORIGINS=http://localhost:5173` is in `.env` |
