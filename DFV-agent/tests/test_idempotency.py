"""
Idempotency test for the DFV worker.

Proves: if a message for a session/correlation_id that's already marked
'done' in MongoDB arrives again (duplicate delivery, consumer restart,
manual retry, etc.), the worker skips it instead of re-running CrewAI
or overwriting the completed output.

Usage:
    1. Make sure the DFV consumer (workers/dfv_consumer.py) is already
       running and has completed at least one job.
    2. Run this script:
           uv run python -u -m tests.test_idempotency
    3. Watch the consumer's terminal — you should see a line like:
           [correlation=...] Already processed (idempotency check) — skipping
       appear almost instantly (no CrewAI run, no token usage logs).
    4. This script also independently verifies via Mongo that the
       'completed_at' timestamp did NOT change after the duplicate
       message was sent — proof the output wasn't recomputed/overwritten.
"""

import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from aiokafka import AIOKafkaProducer

from models.schema import DFVJobMessage, DFVJobPayload

KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
DFV_TOPIC = "userSession.dfv"
MONGO_URI = "mongodb://127.0.0.1:27017"
DB_NAME = "agis"
USER_SESSIONS_COLLECTION = "userSessions"


async def find_a_done_session(db):
    """Grab any session already marked done, to reuse its IDs for the duplicate."""
    doc = await db[USER_SESSIONS_COLLECTION].find_one({"dfv.status": "done"})
    if not doc:
        raise RuntimeError(
            "No session with dfv.status='done' found in Mongo. "
            "Run the consumer + producer at least once first."
        )
    return doc


async def main():
    mongo_client = AsyncIOMotorClient(MONGO_URI)
    db = mongo_client[DB_NAME]

    done_doc = await find_a_done_session(db)
    session_id = done_doc["_id"]
    dfv = done_doc["dfv"]
    correlation_id = dfv["correlation_id"]
    idea_name = dfv["idea_name"]
    completed_at_before = dfv["completed_at"]

    print(f"[Test] Found completed session: {session_id} ({idea_name})")
    print(f"[Test] completed_at BEFORE duplicate: {completed_at_before}")
    print(f"[Test] Republishing duplicate message with SAME correlation_id={correlation_id} ...")

    duplicate_job = DFVJobMessage(
        userSession_id=session_id,
        correlation_id=correlation_id,
        idea_name=idea_name,
        payload=DFVJobPayload(
            desirability="duplicate test - should never be processed",
            feasibility="duplicate test - should never be processed",
            viability="duplicate test - should never be processed",
        ),
    )

    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    try:
        await producer.send_and_wait(
            DFV_TOPIC,
            value=duplicate_job.model_dump_json().encode("utf-8"),
            key=session_id.encode("utf-8"),
        )
    finally:
        await producer.stop()

    print("[Test] Duplicate sent. Waiting 15s for the consumer to (not) process it...")
    await asyncio.sleep(15)

    updated_doc = await db[USER_SESSIONS_COLLECTION].find_one({"_id": session_id})
    completed_at_after = updated_doc["dfv"]["completed_at"]

    print(f"[Test] completed_at AFTER duplicate:  {completed_at_after}")

    if completed_at_before == completed_at_after:
        print("[Test] PASS — completed_at unchanged. Idempotency check worked, "
              "job was NOT reprocessed.")
    else:
        print("[Test] FAIL — completed_at changed. The job was reprocessed! "
              "Idempotency check did not work.")

    mongo_client.close()


if __name__ == "__main__":
    asyncio.run(main())
