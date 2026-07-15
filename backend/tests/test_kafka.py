import asyncio
from aiokafka import AIOKafkaConsumer

async def main():
    consumer = AIOKafkaConsumer(
        bootstrap_servers="localhost:9092"
    )

    await consumer.start()
    print("Topics:", await consumer.topics())
    await consumer.stop()

asyncio.run(main())
