# test_kafka.py
import asyncio
from app.kafka.producer import KafkaProducerClient, kafka_producer
from app.exceptions.base import AppException, KafkaPublishError
from app.kafka.payloads import TIPSCPayload

async def run_tests():
    print("Running Kafka Producer Verification...")

    # 1. Singleton Check
    client_a = KafkaProducerClient()
    assert client_a is kafka_producer, "Fail: Exported instance does not match."
    client_b = KafkaProducerClient()
    assert client_a is client_b, "Fail: Multiple instances created."
    print("✅ Singleton pattern verified.")

    # 2. Exception Hierarchy Check
    assert issubclass(KafkaPublishError, AppException), "Fail: KafkaPublishError does not inherit from AppException."
    print("✅ Exception hierarchy verified.")

    # 3. Publish Test
    print("Starting Kafka Producer...")
    await kafka_producer.initialize()
    
    # Create a mock payload matching the required schema
    test_payload = TIPSCPayload(
        session_id="ses_test_123",
        team_id="team_test_456",
        student_id="usr_test_789",
        flow="tipsc",
        problem_statement="Test problem statement",
        idea="Test idea"
    )

    try:
        correlation_id = await kafka_producer.publish("userSession.tipsc", test_payload)
        print(f"✅ Publish successful! Correlation ID: {correlation_id}")
    except Exception as e:
        print(f"❌ Publish failed: {e}")
    finally:
        await kafka_producer.shutdown()

if __name__ == "__main__":
    asyncio.run(run_tests())