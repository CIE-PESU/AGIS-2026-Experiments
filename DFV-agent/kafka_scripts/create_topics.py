"""
One-time setup: creates the Kafka topics the DFV worker needs.

Run this once against your local KRaft broker before testing the
producer/consumer. Safe to re-run — skips topics that already exist.

Usage:
    python kafka/create_topics.py
"""

import asyncio
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError

KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"

TOPICS = [
    NewTopic(name="userSession.dfv", num_partitions=3, replication_factor=1),
    NewTopic(name="userSession.dfv.dlq", num_partitions=1, replication_factor=1),
    NewTopic(name="userSession.notifications", num_partitions=3, replication_factor=1),
]


async def create_topics():
    admin = AIOKafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await admin.start()

    try:
        for topic in TOPICS:
            try:
                await admin.create_topics([topic])
                print(f"[OK] Created topic: {topic.name} (partitions={topic.num_partitions})")
            except TopicAlreadyExistsError:
                print(f"[SKIP] Topic already exists: {topic.name}")
    finally:
        await admin.close()


if __name__ == "__main__":
    asyncio.run(create_topics())