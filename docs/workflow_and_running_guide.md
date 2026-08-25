# AGIS Setup, Workflow & Deployment Guide

This document provides a comprehensive, step-by-step guide for setting up, configuring, and running the AGIS platform (FastAPI backend, React frontend, Kafka workers, MongoDB, and CrewAI agents) on any fresh system.

---

## 1. System Requirements & Prerequisites

Ensure the target system has the following software installed:

* **Python**: `v3.12+`
* **Node.js**: `v18+` & `npm`
* **Docker & Docker Compose**: Installed and running
* **Local LLM Server (LM Studio / Ollama / vLLM)**:
  * Local OpenAI-compatible server running at `http://127.0.0.1:1234/v1`
  * Model loaded (e.g., `qwen2.5-32b-instruct` or `bonsai-8b`)
* **Serper API Key**: For web search capabilities in CrewAI agents (get from [serper.dev](https://serper.dev)).

---

## 2. Infrastructure Setup (Docker)

Start MongoDB and Apache Kafka using Docker Compose:

```bash
# Navigate to the backend directory
cd backend

# Launch MongoDB (27017) and Kafka (9092) in detached mode
docker compose up -d
```

### Services Started:

* **MongoDB**: `mongodb://localhost:27017`
* **Kafka Broker**: `localhost:9092`
* **Zookeeper**: `localhost:2181`

---

## 3. Environment Configuration (`.env`)

### A. Backend Configuration (`backend/.env`)

Copy the template environment file:

```bash
cd backend
cp .env.example .env
```

Ensure `backend/.env` contains:

```env
# Database & Messaging
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=pesu_agis
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Auth & Secrets
JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
WORKER_INTERNAL_SECRET=your-shared-internal-worker-secret

# LLM & Search
LM_STUDIO_URL=http://localhost:1234/v1
OPENAI_API_KEY=lm-studio
OPENAI_MODEL_NAME=qwen2.5-32b-instruct
SERPER_API_KEY=your_serper_api_key_here

# App Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### B. Agent Environment Configuration (`DFV-agent/.env`, `TIPSC-Agent/.env`)

Ensure agent directories have `.env` configured pointing to the same LLM and Serper key:

```env
LM_STUDIO_URL=http://localhost:1234/v1
OPENAI_API_KEY=lm-studio
OPENAI_MODEL_NAME=qwen2.5-32b-instruct
SERPER_API_KEY=your_serper_api_key_here
```

---

## 4. One-Time Database Migration

Run the session team synchronization script to align any historical diverged `Session.team_id` records with `User.team_id`:

```bash
# From workspace root
python backend/scripts/migrate_session_teams.py
```

---

## 5. Execution Commands (Services Setup)

Run each of the following components in separate terminal windows:

### Terminal 1: Local LLM Server (LM Studio / Ollama)

1. Open LM Studio (or your local LLM host).
2. Load model (e.g. `qwen2.5-32b-instruct`).
3. Start local server at `http://127.0.0.1:1234/v1`.

### Terminal 2: FastAPI Backend Server

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run Uvicorn server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

* Backend API documentation will be accessible at `http://localhost:8000/docs`.

### Terminal 3: React Frontend Application

```bash
cd frontend
npm install

# Start Vite development server
npm run dev
```

* Web application will be accessible at `http://localhost:5173`.

### Terminal 4: Combined Agent Worker (DFV & Discovery)

```bash
cd backend
source .venv/bin/activate
python -m workers.combined_agent_worker
```

---

## 6. Verification & Testing Commands

### A. Run Automated Unit Tests

Run the Pytest suite covering authorization, team reassignment, and comment services:

```bash
# From workspace root
pytest backend/tests
```

### B. Run API Smoke Tests

Run end-to-end API verification against a running backend instance:

```bash
python backend/scripts/smoke_test.py
python backend/scripts/test_api_comments.py
```

---

## 7. Operational Workflow & Architecture

```
User Browser (React Frontend :5173)
        │
        ▼ HTTP REST / JWT
FastAPI Backend (:8000) ──────────────► MongoDB (:27017)
        │                                  ▲
        ▼ Kafka Event                      │ DB Direct Write
Kafka Topics ──────────────────────────────┤
  • userSession.dfv                        │
  • userSession.discovery                  │
        │                                  │
        ▼ Kafka Consumer                   │
Background Workers ────────────────────────┘
  • combined_agent_worker.py
        │
        ▼ Local LLM API
LM Studio / Ollama (:1234/v1)
```

1. **Session Creation**: Student creates a session via Frontend -> Backend writes to MongoDB (`status: queued`) and emits Kafka event to `userSession.tipsc`.
2. **TIPSC Evaluation**: `tipsc_worker.py` uses asyncio event, invokes CrewAI TIPSC agents against LM Studio, and updates session to `tipsc_completed`.
3. **DFV Evaluation**: Student triggers DFV -> Backend emits to `userSession.dfv` -> `combined_agent_worker.py` evaluates Desirability, Feasibility, Viability and sets status to `dfv_completed`.
4. **Customer Discovery Planning**: Student triggers Discovery -> Backend emits to `userSession.discovery` -> Worker generates JTBD interview guide and sets status to `completed`.
5. **Real-time Status Sync**: Frontend polls `GET /api/v1/sessions/{id}` to display progress dynamically.
