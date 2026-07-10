import json
from kafka import KafkaConsumer
from main import run_analysis

results_store: dict = {}

def start_worker():
    consumer = KafkaConsumer(
        'dfv_analysis_jobs',
        bootstrap_servers='127.0.0.1:9092',
        group_id='dfv_worker_group',
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    print("[Worker] 👂 Listening for Kafka messages... (CTRL+C to stop)")

    for message in consumer:
        job = message.value
        idea_name = job["idea_name"]
        payload = job["payload"]

        print(f"\n[Worker] 🚀 Starting: {idea_name} | offset: {message.offset}")

        try:
            # run_analysis() is a plain sync function (crew.kickoff(...)),
            # not async — call it directly, no asyncio.run() needed.
            result = run_analysis(payload)

            try:
                parsed = json.loads(result.raw)
            except Exception:
                parsed = {"raw": result.raw}

            results_store[idea_name] = parsed

            print(f"[Worker] ✅ Done: {idea_name}")
            print(f"[Worker] Decision: {parsed.get('final_decision', {}).get('status', 'unknown')}")

            consumer.commit()

        except Exception as e:
            print(f"[Worker] ❌ ERROR: {e}")

if __name__ == "__main__":
    start_worker()
