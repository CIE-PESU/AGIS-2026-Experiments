"""
SessionStatus enum — single source of truth for all session states.
Used by models, state machine, and repositories.
"""

from enum import Enum


class SessionStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    TIPSC_RUNNING = "tipsc_running"
    TIPSC_COMPLETED = "tipsc_completed"
    TIPSC_FAILED = "tipsc_failed"
    DFV_WAITING = "dfv_waiting"
    DFV_RUNNING = "dfv_running"
    DFV_COMPLETED = "dfv_completed"
    DFV_FAILED = "dfv_failed"
    DISCOVERY_WAITING = "discovery_waiting"
    DISCOVERY_RUNNING = "discovery_running"
    DISCOVERY_FAILED = "discovery_failed"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"

    # States where a flow is actively running — cannot archive during these
    @classmethod
    def running_states(cls) -> set["SessionStatus"]:
        return {
            cls.TIPSC_RUNNING,
            cls.DFV_RUNNING,
            cls.DISCOVERY_RUNNING,
        }

    # Terminal states — no further transitions allowed (except archiving)
    @classmethod
    def terminal_states(cls) -> set["SessionStatus"]:
        return {cls.COMPLETED, cls.FAILED, cls.ARCHIVED}
