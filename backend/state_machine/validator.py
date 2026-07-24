"""
Transition validator — pure logic, no DB/Kafka/model imports.

Called by flow_service.py (Day 2, Sujal) before any Kafka publish or DB
write. If the transition is forbidden, callers should catch
InvalidStateTransitionError and translate it to a 409.
"""

from state_machine.exceptions import InvalidStateTransitionError
from state_machine.states import SessionStatus
from state_machine.transitions import ALLOWED_TRANSITIONS


def validate_transition(
    current_status: SessionStatus, target_status: SessionStatus
) -> None:
    """
    Raise InvalidStateTransitionError if moving from current_status to
    target_status isn't allowed. Returns None (no exception) if it's fine.
    """
    allowed_next_states = ALLOWED_TRANSITIONS.get(current_status, frozenset())

    if target_status not in allowed_next_states:
        raise InvalidStateTransitionError(current_status, target_status)


def get_allowed_next_states(current_status: SessionStatus) -> frozenset[SessionStatus]:
    """Helper for callers (e.g. API responses) that want to expose what a
    session can legally do next, without duplicating the transition map."""
    return ALLOWED_TRANSITIONS.get(current_status, frozenset())