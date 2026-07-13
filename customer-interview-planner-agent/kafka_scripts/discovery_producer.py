"""
aiokafka producer for the Discovery (Customer Discovery Planner / JTBD) flow.

In production this logic lives inside backend/kafka/ and gets called from
POST /userSession/{id}/trigger/discovery. This file exists so the workers
team can publish test jobs without depending on the backend service being
up, and without depending on real TIPSC/DFV output being available yet.
"""

import uuid
import asyncio
from aiokafka import AIOKafkaProducer

from models.schema import DiscoveryJobMessage, DiscoveryJobPayload

KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
DISCOVERY_TOPIC = "userSession.discovery"


async def publish_discovery_job(
    producer: AIOKafkaProducer,
    userSession_id: str,
    payload: DiscoveryJobPayload,
) -> str:
    """Publish a Discovery job. Returns the correlation_id for tracking."""
    correlation_id = str(uuid.uuid4())

    message = DiscoveryJobMessage(
        userSession_id=userSession_id,
        correlation_id=correlation_id,
        payload=payload,
    )

    await producer.send_and_wait(
        DISCOVERY_TOPIC,
        value=message.model_dump_json().encode("utf-8"),
        key=userSession_id.encode("utf-8"),  # same session always lands on same partition
    )

    print(f"[Producer] Queued discovery job | session={userSession_id} | correlation={correlation_id}")
    return correlation_id


async def main():
    """Manual test harness — uses the same sample data as customer_interview_planner.py's __main__ block."""
    from customer_interview_planner import SAMPLE_DISCOVERY_INPUTS

    payload = DiscoveryJobPayload(**SAMPLE_DISCOVERY_INPUTS)

    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    try:
        await publish_discovery_job(
            producer,
            userSession_id=str(uuid.uuid4()),  # fake session id for local testing
            payload=payload,
        )
    finally:
        await producer.stop()

    print("\n[Producer] Discovery job sent to Kafka.")


if __name__ == "__main__":
    asyncio.run(main())
