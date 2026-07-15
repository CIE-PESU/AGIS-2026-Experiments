"""
One-off check: does userSession.notifications contain a message for the
"discovery" flow? Prints every matching message found, then exits.

Usage:
    uv run python -u -m kafka_scripts.check_discovery_notifications
"""

import asyncio
import json
from aiokafka import AIOKafkaConsumer

KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
NOTIFICATIONS_TOPIC = "userSession.notifications"


async def main():
    consumer = AIOKafkaConsumer(
        NOTIFICATIONS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="check-discovery-notifications-adhoc",  # unique, always reads from earliest
        auto_offset_reset="earliest",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )
    await consumer.start()

    found = []
    try:
        # Read whatever's available for up to 5 seconds, then stop.
        while True:
            try:
                batch = await asyncio.wait_for(consumer.getmany(timeout_ms=1000), timeout=5)
            except asyncio.TimeoutError:
                break
            if not batch:
                break
            for tp, messages in batch.items():
                for msg in messages:
                    if msg.value.get("flow") == "discovery":
                        found.append(msg.value)
    finally:
        await consumer.stop()

    if found:
        print(f"Found {len(found)} discovery notification(s):\n")
        for note in found:
            print(json.dumps(note, indent=2))
    else:
        print("No discovery notifications found in the topic.")


if __name__ == "__main__":
    asyncio.run(main())
