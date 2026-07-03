"""
kafka/payloads.py — Typed Pydantic models for every Kafka message payload.

Using Pydantic ensures that every message published to Kafka is schema-validated
before serialisation. Workers must deserialise using the same schema.

Serialisation: call `.model_dump_json()` to get the JSON string for the Kafka value.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TIPSCEventPayload(BaseModel):
    """
    Payload published to `userSession.tipsc` topic when a session is created.

    Workers consume this message and run the TIPSC evaluation.
    correlation_id is stored on the session document so the worker can verify
    it is processing the most recent event (guards against duplicate delivery).
    """

    session_id: str = Field(description="MongoDB ObjectId string of the session.")
    student_id: str = Field(description="SRN or user_id of the student.")
    team_id: str = Field(description="Team identifier.")
    problem_statement: str = Field(description="Problem statement submitted by the student.")
    idea: str = Field(description="Business idea submitted by the student.")
    correlation_id: str = Field(description="UUID4 uniquely identifying this publish event.")
    triggered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the backend published this event.",
    )


class DFVEventPayload(BaseModel):
    """Payload published to `userSession.dfv` topic."""

    session_id: str
    student_id: str
    team_id: str
    problem_statement: str
    idea: str
    desirability_context: Optional[str] = None
    feasibility_context: Optional[str] = None
    viability_context: Optional[str] = None
    correlation_id: str
    triggered_at: datetime = Field(default_factory=datetime.utcnow)


class DiscoveryEventPayload(BaseModel):
    """Payload published to `userSession.discovery` topic."""

    session_id: str
    student_id: str
    team_id: str
    problem_statement: str
    idea: str
    correlation_id: str
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
