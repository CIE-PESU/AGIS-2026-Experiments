"""
core/constants.py — Immutable application-wide constants.

These are NOT secrets. Secrets belong in core/config.py via env vars.
"""


class AuditEvent:
    """All valid audit log event types. Matches api-spec.md Section 5.1."""

    SESSION_CREATED = "SESSION_CREATED"
    TIPSC_TRIGGERED = "TIPSC_TRIGGERED"
    TIPSC_RUNNING = "TIPSC_RUNNING"
    TIPSC_COMPLETED = "TIPSC_COMPLETED"
    TIPSC_FAILED = "TIPSC_FAILED"
    DFV_TRIGGERED = "DFV_TRIGGERED"
    DFV_RUNNING = "DFV_RUNNING"
    DFV_COMPLETED = "DFV_COMPLETED"
    DFV_FAILED = "DFV_FAILED"
    DISCOVERY_TRIGGERED = "DISCOVERY_TRIGGERED"
    DISCOVERY_RUNNING = "DISCOVERY_RUNNING"
    DISCOVERY_COMPLETED = "DISCOVERY_COMPLETED"
    DISCOVERY_FAILED = "DISCOVERY_FAILED"
    COMMENT_ADDED = "COMMENT_ADDED"
    COMMENT_DELETED = "COMMENT_DELETED"
    SESSION_ARCHIVED = "SESSION_ARCHIVED"
    RETRY_TRIGGERED = "RETRY_TRIGGERED"
    LOGIN = "LOGIN"


class UserRole:
    """Role strings as stored in JWT and MongoDB."""

    STUDENT = "student"
    MENTOR = "mentor"
    ADMIN = "admin"
    WORKER = "worker"


class FlowName:
    """Flow identifiers used in Kafka topics and worker API calls."""

    TIPSC = "tipsc"
    DFV = "dfv"
    DISCOVERY = "discovery"
