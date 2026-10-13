# AGIS — Setup, Workflow & Running Guide

> **Fresh clone? Start here.** This is the single source of truth for getting
> the full AGIS platform running locally after pulling the repo.

---

## 1. System Prerequisites

| Tool                    | Version   | Notes                                     |
| ----------------------- | --------- | ----------------------------------------- |
| Python                  | `3.12+`   | Check:`python3 --version`               |
| Node.js & npm           | `18+`     | Check:`node --version`                  |
| Docker & Docker Compose | Latest    | Must be running                           |
| LLM Server              | —         | LM Studio / Ollama / NVIDIA NIM (see §3) |
| Theme Support           | —         | Light/Dark mode toggle (persisted)        |

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

## 2. Infrastructure — Start Docker Services

The `docker-compose.yml` lives in `backend/`. It starts **Kafka** (KRaft mode,
no Zookeeper) and optionally MongoDB if you add it.

```bash
docker compose -f backend/docker-compose.yml up -d
```

> **Note**: MongoDB is **not** in the compose file — the app connects to
> `mongodb://localhost:27017` by default. Install MongoDB locally or add a
> `mongo` service to the compose file if needed.

### Services started

| Service         | Port      | URI                           |
| --------------- | --------- | ----------------------------- |
| Kafka (KRaft)   | `9092`    | `localhost:9092`            |
| MongoDB (local) | `27017`   | `mongodb://localhost:27017` |

To stop:

```bash
docker compose -f backend/docker-compose.yml down
```

---

## 3. Running the Platform — Two Options

### Option A: One-Command Dev Server (Recommended)

Start **all services** (backend, workers, frontend) with one command:

```bash
python3 dev.py
```

This starts:
- FastAPI backend (port 8000) — with MongoDB, Kafka, TIPSC engine initialization
- Combined Agent Worker (DFV + Discovery) — with Kafka retry logic
- Notification Worker
- React Frontend (Vite, port 5173) — starts after workers are ready

> **Note**: The script waits ~48s before starting frontend to ensure backend/workers are fully initialized.

**Frontend**: http://localhost:5173
**Backend API**: http://localhost:8000/docs
**Health**: http://localhost:8000/health

---

### Option B: Manual Multi-Terminal (Legacy / Advanced)

Open **5 terminal windows**, each with the venv activated:

```bash
# In each terminal:
source .venv/bin/activate
```

---

#### Terminal 1 — LLM Server

**Option A — Local LM Studio**

1. Open LM Studio → load a model (e.g. `qwen3.5-9b`)
2. Start the local server → it listens on `http://127.0.0.1:1234/v1`

**Option B — NVIDIA NIM / cloud**

- Nothing to start locally; just ensure `OPENAI_API_KEY` is set in `.env`

---

#### Terminal 2 — FastAPI Backend

```bash
source .venv/bin/activate
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: **http://localhost:8000/docs**
- Health check: **http://localhost:8000/health**
- Quickstart evaluation: `POST /api/v1/quickstart/evaluate` (in-process, no worker needed)

---

#### Terminal 3 — Combined Agent Worker (DFV + Discovery)

```bash
source .venv/bin/activate
cd backend
python -m workers.combined_agent_worker
```

Consumes from Kafka topics:
- `userSession.dfv`
- `userSession.discovery`

**Worker Features**:
- Exponential backoff retry (max 10 attempts) for Kafka consumer startup
- `request_timeout_ms: 60000` for long-running agent workloads
- Loads `.env` via `python-dotenv` for agent environment variables

---

#### Terminal 4 — Notification Worker

```bash
source .venv/bin/activate
cd backend
python -m workers.notification_worker
```

---

#### Terminal 5 — React Frontend

```bash
cd frontend
npm run dev
```

- Web app: **http://localhost:5173**

---

## 4. One-Time Database Migration

Only needed if you have pre-existing data from an older schema:

```bash
source .venv/bin/activate
python backend/scripts/migrate_session_teams.py
```

---

## 5. Verification & Testing

### Run unit tests

```bash
source .venv/bin/activate
pytest tests/
```

**Current status**: **488/488 backend unit tests passing** (0 failures)

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

## 6. UI Features

### Dark Mode

The frontend supports **light/dark theme switching** with true black (`#000000`) in dark mode:

- **Toggle location**: Top-right corner of all authenticated pages (Workspace, Quickstart, Mentor Dashboard, Admin Dashboard) + Landing Page navbar
- **Persistence**: User preference saved to `localStorage` and restored on revisit
- **System preference**: On first visit, respects `prefers-color-scheme` media query
- **Dark mode colors**: True black (`#000000`) backgrounds; CSS custom properties in `src/index.css` with `.dark` class
- **Implementation**: `ThemeProvider` in `src/context/ThemeContext.tsx`; toggle component in `src/components/ui/theme-toggle.tsx`
- **Three Phases section**: Navy blue gradient (`gradient-navy`) in dark mode
- **All hardcoded colors migrated** to CSS variables (`bg-background`, `bg-card`, `text-foreground`, `text-muted-foreground`, etc.)

### Landing Page Updates

- **Navbar auth-aware**: Shows "Quickstart" + "Sign In" when unauthenticated; "Workspace" + "Logout" when authenticated
- **Pipeline flow**: "Submit Idea → Ethics → TIPSC → DFV → Customer Discovery" (5 steps)
- **Phase labels**: White text in both light and dark mode
- **CTA buttons**: "Try Quickstart" → "Quickstart"; "Try Quickstart Evaluation" → "Quickstart Evaluation"
- **Hero CTA**: "Get Started Now" links to `/login?redirect=/quickstart`
- **Dark mode sections**: Three Phases section and Bottom CTA use navy gradient (`dark:gradient-navy`)

### Quickstart Flow Updates

- **Back button**: "Back to Workspace" → "Back to Home" (links to `/` instead of `/workspace`)
- **Result cards**: Dark mode compatible with CSS variables
- **Error states**: Dark mode compatible (red/amber/green with proper contrast)

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
    • combined_agent_worker.py (DFV + Discovery)
    • notification_worker.py
        │
        ▼  OpenAI-compatible API
  LLM Server (LM Studio / NVIDIA NIM)
```

### Request flow

1. **Quickstart Evaluation (Optional)** → Frontend → `POST /api/v1/quickstart/evaluate` → Quickstart Agent (Ethics 3 + TIPSC 4 + DFV 3 = 10 parameters) runs in-process, returns GREEN/YELLOW/RED traffic lights with reasons and advice
2. **Session Created** → Frontend → Backend writes to MongoDB (`status: queued`) → emits `userSession.tipsc`
3. **Ethics Gate** → TIPSC Agent evaluates Harm Vector, Legal Risk, Problem-Solution Integrity → `ethics_completed`
4. **TIPSC Evaluation** → TIPSC Agent scores Timely, Importance, Profitable, Solvable → `tipsc_completed`
5. **DFV Evaluation** → Student triggers DFV → Backend emits `userSession.dfv` → `combined_agent_worker` evaluates Desirability / Feasibility / Viability → `dfv_completed`
6. **Customer Discovery** → Student triggers Discovery → Backend emits `userSession.discovery` → Worker generates JTBD interview guide → `completed`
7. **Real-time Updates** → Frontend polls `GET /api/v1/sessions/{id}` to show live progress

---

## 8. Quick-Reference Cheat Sheet

```bash
# === ONCE (fresh clone) ===
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env
cd frontend && npm install && cd ..

# === EVERY SESSION (One-Command - Recommended) ===
docker compose -f backend/docker-compose.yml up -d   # T0: infra
python3 dev.py                                          # T1: starts everything

# === EVERY SESSION (Manual - Legacy) ===
docker compose -f backend/docker-compose.yml up -d   # T0: infra
source .venv/bin/activate && cd backend && uvicorn main:app --reload --port 8000   # T2: API
source .venv/bin/activate && cd backend && python -m workers.combined_agent_worker # T3: DFV worker
source .venv/bin/activate && cd backend && python -m workers.notification_worker   # T4: notifs
cd frontend && npm run dev                                                           # T5: UI
```

---

## 9. Troubleshooting

| Symptom                              | Fix                                                                                                       |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError`              | Make sure venv is activated:`source .venv/bin/activate`                                                 |
| `Connection refused` on port 9092  | `docker compose -f backend/docker-compose.yml up -d`                                                    |
| `Connection refused` on port 27017 | Start MongoDB locally or add it to docker-compose                                                         |
| LLM agent times out                  | Verify your LLM server is running and`LM_STUDIO_URL` / `OPENAI_API_KEY` are set correctly in `.env` |
| `JWT_SECRET` error on startup      | Ensure`.env` has a 32+ character `JWT_SECRET` value                                                   |
| Frontend can't reach backend         | Check`CORS_ALLOWED_ORIGINS=http://localhost:5173` is in `.env`                                        |
| Kafka consumer timeout               | Worker has retry logic (max 10 attempts, exponential backoff); check Kafka is running                    |
| `OPENAI_MODEL_NAME` error in worker | Ensure `.env` is loaded (worker auto-loads root `.env` via `python-dotenv`)                             |

---