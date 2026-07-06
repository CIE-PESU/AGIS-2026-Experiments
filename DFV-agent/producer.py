import json
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='127.0.0.1:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def publish_analysis_job(idea_name: str, idea_payload: dict):
    job = {"idea_name": idea_name, "payload": idea_payload}
    future = producer.send('dfv_analysis_jobs', value=job)
    result = future.get(timeout=10)
    print(f"[Producer] ✅ Queued: {idea_name} → offset {result.offset}")

from main import ggls, sncc, blnkt

if __name__ == "__main__":
    publish_analysis_job("Google Glass", ggls)
    publish_analysis_job("SNACCED", sncc)
    publish_analysis_job("Blinkit", blnkt)
    producer.flush()
    print("\n[Producer] All jobs sent to Kafka.")
