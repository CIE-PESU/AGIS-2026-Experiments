# Execution sequences

## Session and TIPSC

```mermaid
sequenceDiagram
    participant Browser
    participant API
    participant MongoDB
    participant TIPSC
    Browser->>API: POST /api/v1/sessions (JWT, idempotency key)
    API->>MongoDB: Owner-scoped create, unique active-session constraint
    API->>TIPSC: Schedule task with run identity
    API-->>Browser: Session response
    TIPSC->>MongoDB: Version/run-guarded stage writes
    alt Founder evidence needed
        TIPSC->>MongoDB: waiting_for_founder and pending question
        Browser->>API: POST followup (answer)
        API->>MongoDB: Atomically claim turn/version
        API->>TIPSC: Schedule reevaluation
    end
    TIPSC->>MongoDB: tipsc_completed or tipsc_failed
    Browser->>API: Poll or authenticated SSE
    API-->>Browser: Authorized session state
```

## DFV and Discovery

```mermaid
sequenceDiagram
    participant Browser
    participant API
    participant MongoDB
    participant Kafka
    participant Worker
    participant Agent
    Browser->>API: Trigger flow (JWT, inputs, optional key)
    API->>MongoDB: Guarded start + correlation + replay record
    API->>Kafka: Publish validated job
    API-->>Browser: 202 with run identity
    Kafka->>Worker: Job delivery
    Worker->>Agent: Isolated cancellable process
    Agent-->>Worker: Output
    Worker->>Worker: Persist callback in SQLite mailbox
    Worker->>API: Authenticated output/failure callback
    API->>MongoDB: Validate run/state/version and persist
    API-->>Worker: Accepted or duplicate
    Worker->>Kafka: Commit offset
    Note over Worker,API: Transient failures retain offset and replay persisted callback
```

Interrupted TIPSC work becomes retryable after timeout; it is not resumed midway through a provider call. See [architecture](backend-arch.md) for concurrency and deployment boundaries.
