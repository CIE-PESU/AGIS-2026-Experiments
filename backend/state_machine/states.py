"""
state_machine/states.py

Single source of truth for the complete AGIS session lifecycle.
"""

from enum import Enum


class SessionStatus(str, Enum):
    # Session creation
    CREATED = "created"
    QUEUED = "queued"

    # TIPSC pipeline
    PRE_EVAL = "pre_eval"
    VALIDATION_RUNNING = "validation_running"
    ETHICS_RUNNING = "ethics_running"
    TIPSC_RUNNING = "tipsc_running"

    # Founder follow-up loop
    WAITING_FOR_FOUNDER = "waiting_for_founder"
    TIPSC_REEVALUATION = "tipsc_reevaluation"

    # TIPSC terminal states
    TIPSC_COMPLETED = "tipsc_completed"
    TIPSC_FAILED = "tipsc_failed"

    # DFV
    DFV_WAITING = "dfv_waiting"
    DFV_RUNNING = "dfv_running"
    DFV_COMPLETED = "dfv_completed"
    DFV_FAILED = "dfv_failed"

    # Discovery
    DISCOVERY_WAITING = "discovery_waiting"
    DISCOVERY_RUNNING = "discovery_running"
    DISCOVERY_FAILED = "discovery_failed"

    # Global terminal states
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


RUNNING_STATES = frozenset(
    {
        SessionStatus.QUEUED,
        SessionStatus.PRE_EVAL,
        SessionStatus.VALIDATION_RUNNING,
        SessionStatus.ETHICS_RUNNING,
        SessionStatus.TIPSC_RUNNING,
        SessionStatus.TIPSC_REEVALUATION,
        SessionStatus.DFV_RUNNING,
        SessionStatus.DISCOVERY_RUNNING,
    }
)


TERMINAL_STATES = frozenset(
    {
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
        SessionStatus.ARCHIVED,
    }
)