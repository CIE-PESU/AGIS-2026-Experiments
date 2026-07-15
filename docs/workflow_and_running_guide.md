# AGIS Backend & Kafka Workers Workflow Guide

This document explains the end-to-end workflow of the AGIS platform, detailing how to run the FastAPI backend, how to run the Kafka worker agents, and the flow of information across the system.

## 1. Prerequisites

Before running the components, ensure the following services are running locally (typically via Docker or native installations):

1. **MongoDB**: Running locally at `mongodb://127.0.0.1:27017`
2. **Apache Kafka**: Running locally at `127.0.0.1:9092`
3. **LM Studio**: Running locally with the appropriate LLM loaded (e.g., Bonsai-8B, Mistral-7B). Ensure the Local Server is enabled at `http://127.0.0.1:1234/v1`.

## 2. Running the API Backend

The backend is a FastAPI application that serves as the single source of truth. It manages sessions, enforces RBAC, handles MongoDB persistence for API routes, and publishes events to Kafka.

**Setup Environment:**

```bash
cd backend
pip install -r requirements.txt
# Copy the example env file and update as needed
cp .env.example .env
```

**Run the Backend:**

```bash
uvicorn main:app --reload --port 8000
```

*Note: The backend publishes to Kafka but does NOT consume messages. It waits for workers to update the session data in MongoDB asynchronously.*

## 3. Running the Kafka Workers (Agents)

The system relies on asynchronous workers that listen to Kafka topics, execute CrewAI agentic pipelines, and update MongoDB directly.

### A. The Combined Agent Worker (DFV & Discovery)

The backend features a unified worker script that consumes from both `userSession.dfv` and `userSession.discovery` topics. It dynamically imports and runs the agents from the `DFV-agent` and `customer-interview-planner-agent` folders.

**To run the combined worker:**

```bash
cd backend
python -m workers.combined_agent_worker
```

*Make sure you have installed the requirements for the agents as well, since `combined_agent_worker.py` imports their logic directly.*

### B. The Preeval / TIPSC Consumer

For the Pre-Evaluation and TIPSC scoring phase, there is a dedicated consumer.

```bash
cd backend
python -m workers.preeval_consumer
```

### C. (Optional) Running Workers Standalone

If you need to test the agents independently of Kafka (e.g., for local debugging), you can run them directly from their respective directories:

**TIPSC-Agent:**

```bash
cd TIPSC-Agent
uv run python -m src.main
```

**Customer Interview Planner (Discovery):**

```bash
cd customer-interview-planner-agent
python main.py
```

## 4. The End-to-End Workflow

Here is how data flows through the platform asynchronously during a complete lifecycle:

### Phase 1: Session Creation (API -> Kafka)

1. **User Action:** Student POSTs their initial idea via the frontend to `/api/v1/sessions`.
2. **Backend Action:**
   - Validates input and authenticates the student.
   - Writes a new session document to MongoDB with `status = CREATED`.
   - Publishes an event to the `userSession.tipsc` Kafka topic.
   - Updates MongoDB `status = QUEUED` and returns `200 OK` to the frontend.

### Phase 2: TIPSC Worker Execution

1. **Worker Consumption:** The TIPSC Kafka consumer picks up the event.
2. **Execution:** It triggers the CrewAI TIPSC pipeline (Pre-evaluation, Market Validation, Regulatory Mapping, Ethics Screen, TIPSC scoring).
3. **Database Write:** The worker writes the final output directly to the session document in MongoDB and sets `status = TIPSC_COMPLETED`.
4. **Notification:** The worker publishes a completion event to `userSession.notifications`.

### Phase 3: DFV Flow

1. **User Action:** Student triggers the DFV analysis.
2. **Backend Action:** Publishes to `userSession.dfv` topic.
3. **Worker Consumption:** The `combined_agent_worker` consumes the DFV message.
4. **Execution:** Evaluates Desirability, Feasibility, and Viability using CrewAI.
5. **Database Write:** The worker updates the MongoDB session with the DFV output and sets `status = DFV_COMPLETED`.

### Phase 4: Customer Discovery Planner Flow

1. **User Action:** Student triggers the discovery planner.
2. **Backend Action:** Publishes to `userSession.discovery` topic.
3. **Worker Consumption:** The `combined_agent_worker` consumes the Discovery message.
4. **Execution:** Generates a structured Jobs-To-Be-Done (JTBD) interview plan.
5. **Database Write:** The worker updates MongoDB with the discovery plan and sets the session `status = COMPLETED`.

Throughout this entire process, the **React frontend polls the backend** (`GET /api/v1/sessions/{id}`) every few seconds to reflect real-time status changes and unlock subsequent phases as the Kafka workers finish their tasks.
