"""
tests/contract/test_schemas.py — Contract tests for Kafka message schemas.

Verifies that serialisation/deserialisation round-trips are stable between
the backend and the AI-agent worker repos. Run with:

    pytest backend/tests/contract/ -v

These tests do NOT require a running Kafka broker or MongoDB instance.
They only validate Python object ↔ JSON round-trips.
"""

import pytest


# ---------------------------------------------------------------------------
# Kafka payload contract tests (kafka/payloads.py)
# ---------------------------------------------------------------------------

class TestTIPSCPayload:
    """Verify TIPSCEventPayload round-trips cleanly."""

    def test_roundtrip(self):
        from kafka.payloads import TIPSCEventPayload
        payload = TIPSCEventPayload(
            session_id="507f1f77bcf86cd799439011",
            student_id="PES2UG22CS001",
            team_id="team_001",
            problem_statement="We solve food waste on campus using IoT sensors.",
            idea="CampusBite: ML-driven demand prediction for food courts.",
            correlation_id="cor_abc123",
        )
        reconstructed = TIPSCEventPayload.model_validate_json(payload.model_dump_json())
        assert reconstructed.session_id == payload.session_id
        assert reconstructed.correlation_id == payload.correlation_id

    def test_required_fields_present(self):
        from kafka.payloads import TIPSCEventPayload
        payload = TIPSCEventPayload(
            session_id="abc",
            student_id="PES2UG22CS001",
            team_id="team_001",
            problem_statement="Problem",
            idea="Idea",
            correlation_id="cor_xyz",
        )
        dumped = payload.model_dump()
        for field in ("session_id", "student_id", "team_id", "problem_statement", "idea", "correlation_id"):
            assert field in dumped, f"Required field '{field}' missing from payload"


class TestDFVPayload:
    """Verify DFVEventPayload round-trips cleanly."""

    def test_roundtrip(self):
        from kafka.payloads import DFVEventPayload
        payload = DFVEventPayload(
            session_id="507f1f77bcf86cd799439011",
            student_id="PES2UG22CS001",
            team_id="team_001",
            problem_statement="Problem",
            idea="Idea",
            correlation_id="cor_dfv_001",
            desirability_context="Users want this badly.",
            feasibility_context="We can build it.",
            viability_context="We can charge for it.",
        )
        reconstructed = DFVEventPayload.model_validate_json(payload.model_dump_json())
        assert reconstructed.desirability_context == payload.desirability_context
        assert reconstructed.viability_context == payload.viability_context


class TestDiscoveryPayload:
    """Verify DiscoveryEventPayload round-trips cleanly."""

    def test_roundtrip(self):
        from kafka.payloads import DiscoveryEventPayload
        payload = DiscoveryEventPayload(
            session_id="507f1f77bcf86cd799439011",
            student_id="PES2UG22CS001",
            team_id="team_001",
            problem_statement="Problem",
            idea="Idea",
            correlation_id="cor_disc_001",
            tipsc_summary="Strong TIPSC result.",
            dfv_summary="GO decision from DFV.",
        )
        reconstructed = DiscoveryEventPayload.model_validate_json(payload.model_dump_json())
        assert reconstructed.tipsc_summary == payload.tipsc_summary


# ---------------------------------------------------------------------------
# Session model contract tests
# ---------------------------------------------------------------------------

class TestSessionModel:
    """Verify Session Beanie model fields are present and typed correctly."""

    def test_state_history_field_exists(self):
        from models.session import Session, StateTransition
        import inspect
        fields = Session.model_fields
        assert "state_history" in fields, "state_history field missing from Session model"

    def test_state_transition_roundtrip(self):
        from models.session import StateTransition
        t = StateTransition(
            from_status="created",
            to_status="queued",
            actor="system",
            trigger="session_created",
        )
        data = t.model_dump()
        assert data["from_status"] == "created"
        assert data["to_status"] == "queued"
        assert "timestamp" in data

    def test_session_required_fields(self):
        from models.session import Session
        required = ["team_id", "student_id", "problem_statement", "idea", "status"]
        for field in required:
            assert field in Session.model_fields, f"Required field '{field}' missing from Session"
