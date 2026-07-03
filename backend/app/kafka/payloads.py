# backend/app/kafka/payloads.py
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

def generate_uuid_str() -> str:
    return str(uuid.uuid4())

def get_iso_timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

class KafkaBasePayload(BaseModel):
    event_id: str = Field(default_factory=generate_uuid_str)
    correlation_id: str = Field(default_factory=generate_uuid_str)
    session_id: str
    team_id: str
    student_id: str
    flow: str
    timestamp: str = Field(default_factory=get_iso_timestamp)
    schema_version: str = "1.0"

class TIPSCPayload(KafkaBasePayload):
    problem_statement: str
    idea: str

class DFVPayload(KafkaBasePayload):
    desirability_context: str
    feasibility_context: str
    viability_context: str

class DiscoveryPayload(KafkaBasePayload):
    problem_statement: str
    idea: str
    tipsc_summary: str
    dfv_summary: str