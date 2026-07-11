"""
Session status enum.

This is the single source of truth for every state a session can be in.
Nothing outside this module should hardcode a status string — always
import SessionStatus.
"""

from enum import Enum


class SessionStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"

    TIPSC_RUNNING = "tipsc_running"
    WAITING_FOR_FOUNDER = "waiting_for_founder"
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


# States in which a worker (or the backend, for QUEUED) is actively doing
# something. A session can never be archived while it's in one of these —
# that's the "ANY (non-running) → ARCHIVED" rule from the transition map.
RUNNING_STATES = frozenset(
    {
        SessionStatus.TIPSC_RUNNING,
        SessionStatus.DFV_RUNNING,
        SessionStatus.DISCOVERY_RUNNING,
    }
)

# Terminal states — nothing can transition out of these except... nothing.
# Included here for use by services/tests that need to check "is this session done".
TERMINAL_STATES = frozenset(
    {
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
        SessionStatus.ARCHIVED,
    }
)