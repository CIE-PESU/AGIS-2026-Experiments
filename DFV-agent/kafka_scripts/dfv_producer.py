"""
aiokafka producer for the DFV flow.

In production this logic lives inside backend/kafka/ and gets called from
POST /userSession/{id}/trigger/dfv. This file exists so the workers team
can publish test jobs without depending on the backend service being up.
"""

import json
import uuid
import asyncio
from aiokafka import AIOKafkaProducer

from models.schema import DFVJobMessage, DFVJobPayload

KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
DFV_TOPIC = "userSession.dfv"


async def publish_dfv_job(
    producer: AIOKafkaProducer,
    userSession_id: str,
    idea_name: str,
    payload: DFVJobPayload,
) -> str:
    """Publish a DFV job. Returns the correlation_id for tracking."""
    correlation_id = str(uuid.uuid4())

    message = DFVJobMessage(
        userSession_id=userSession_id,
        correlation_id=correlation_id,
        idea_name=idea_name,
        payload=payload,
    )

    await producer.send_and_wait(
        DFV_TOPIC,
        value=message.model_dump_json().encode("utf-8"),
        key=userSession_id.encode("utf-8"),  # same session always lands on same partition
    )

    print(f"[Producer] Queued: {idea_name} | session={userSession_id} | correlation={correlation_id}")
    return correlation_id


async def main():
    """Manual test harness — mirrors old producer.py's __main__ block."""
    from main import ggls, sncc, blnkt

    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()

    try:
        for idea_name, raw in [("Google Glass", ggls), ("SNACCED", sncc), ("Blinkit", blnkt)]:
            await publish_dfv_job(
                producer,
                userSession_id=str(uuid.uuid4()),  # fake session id for local testing
                idea_name=idea_name,
                payload=DFVJobPayload(**raw),
            )
    finally:
        await producer.stop()

    print("\n[Producer] All jobs sent to Kafka.")


if __name__ == "__main__":
    asyncio.run(main())
