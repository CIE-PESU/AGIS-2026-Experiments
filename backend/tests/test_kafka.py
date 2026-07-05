# tests/test_kafka.py
"""
Kafka producer sanity checks.

These tests verify:
  1. The singleton pattern works (one instance shared across the app).
  2. The exception hierarchy is correct (KafkaPublishError IS an AppException).
  3. The payload models instantiate correctly.

Note: Actual Kafka publish is NOT tested here (no broker in unit tests).
The integration smoke test (Vijay's Day 2 B-13 script) covers end-to-end publish.
"""

import pytest

from app.exceptions.base import AppException, KafkaPublishError
from app.kafka.payloads import TIPSCEventPayload, DFVEventPayload, DiscoveryEventPayload
from app.kafka.producer import KafkaProducerClient, kafka_producer


def test_singleton_pattern():
    """KafkaProducerClient should return the same instance on every call."""
    client_a = KafkaProducerClient()
    client_b = KafkaProducerClient()
    assert client_a is client_b, "KafkaProducerClient is not a singleton"
    assert client_a is kafka_producer, "Module-level kafka_producer is not the singleton"


def test_kafka_publish_error_hierarchy():
    """KafkaPublishError must be a subclass of AppException."""
    assert issubclass(KafkaPublishError, AppException), (
        "KafkaPublishError does not inherit from AppException"
    )
    err = KafkaPublishError("test message")
    assert err.http_status == 503
    assert err.error_code == "KAFKA_UNAVAILABLE"


def test_tipsc_payload_instantiation():
    """TIPSCEventPayload should construct and serialize without errors."""
    payload = TIPSCEventPayload(
        session_id="68678a1234567890abcdef12",
        student_id="PES2UG22CS001",
        team_id="team_abc123",
        problem_statement="Students lack affordable study tools.",
        idea="An AI-powered study buddy app.",
        correlation_id="cor_abc123",
    )
    assert payload.session_id == "68678a1234567890abcdef12"
    assert payload.correlation_id == "cor_abc123"
    # Ensure JSON serialization works
    json_str = payload.model_dump_json()
    assert "session_id" in json_str


def test_dfv_payload_instantiation():
    """DFVEventPayload should construct correctly with optional context fields."""
    payload = DFVEventPayload(
        session_id="68678a1234567890abcdef12",
        student_id="PES2UG22CS001",
        team_id="team_abc123",
        problem_statement="Test problem",
        idea="Test idea",
        desirability_context="Users want this because...",
        feasibility_context="We can build this because...",
        viability_context="It will be profitable because...",
        correlation_id="cor_dfv_test",
    )
    assert payload.desirability_context == "Users want this because..."


def test_discovery_payload_instantiation():
    """DiscoveryEventPayload should include tipsc_summary and dfv_summary."""
    payload = DiscoveryEventPayload(
        session_id="68678a1234567890abcdef12",
        student_id="PES2UG22CS001",
        team_id="team_abc123",
        problem_statement="Test problem",
        idea="Test idea",
        tipsc_summary="TIPSC reasoning excerpt...",
        dfv_summary="DFV summary excerpt...",
        correlation_id="cor_discovery_test",
    )
    assert payload.tipsc_summary == "TIPSC reasoning excerpt..."
    assert payload.dfv_summary == "DFV summary excerpt..."