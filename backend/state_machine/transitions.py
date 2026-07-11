"""
The complete allowed-transition map for a session.

This is the ONLY place transitions are defined. `validator.py` reads this
map and nothing else — if a transition isn't listed here, it's forbidden.

Source: backend_4day_plan.md (Sujal — Day 1) and backend-arch.md Section 6.
"""

from state_machine.states import RUNNING_STATES, SessionStatus

# current_status -> set of statuses it is allowed to move to next.
ALLOWED_TRANSITIONS: dict[SessionStatus, frozenset[SessionStatus]] = {
    SessionStatus.CREATED: frozenset({SessionStatus.QUEUED}),
    SessionStatus.QUEUED: frozenset(
        {SessionStatus.TIPSC_RUNNING, SessionStatus.TIPSC_COMPLETED, SessionStatus.TIPSC_FAILED}
    ),
    SessionStatus.TIPSC_RUNNING: frozenset(
        {SessionStatus.TIPSC_COMPLETED, SessionStatus.TIPSC_FAILED}
    ),
    SessionStatus.TIPSC_FAILED: frozenset({SessionStatus.QUEUED}),
    SessionStatus.TIPSC_COMPLETED: frozenset({SessionStatus.DFV_WAITING}),
    SessionStatus.DFV_WAITING: frozenset(
        {SessionStatus.DFV_RUNNING, SessionStatus.DFV_COMPLETED, SessionStatus.DFV_FAILED}
    ),
    SessionStatus.DFV_RUNNING: frozenset(
        {SessionStatus.DFV_COMPLETED, SessionStatus.DFV_FAILED}
    ),
    SessionStatus.DFV_COMPLETED: frozenset({SessionStatus.DISCOVERY_WAITING}),
    SessionStatus.DISCOVERY_WAITING: frozenset(
        {SessionStatus.DISCOVERY_RUNNING, SessionStatus.COMPLETED, SessionStatus.DISCOVERY_FAILED}
    ),
    SessionStatus.DISCOVERY_RUNNING: frozenset(
        {SessionStatus.COMPLETED, SessionStatus.DISCOVERY_FAILED}
    ),
    # Terminal / failure states with no defined next step in the plan.
    # (DFV_FAILED and DISCOVERY_FAILED have no documented retry path today —
    # only TIPSC_FAILED retries. Revisit if product adds retry-from-DFV later.)
    SessionStatus.DFV_FAILED: frozenset(),
    SessionStatus.DISCOVERY_FAILED: frozenset(),
    SessionStatus.COMPLETED: frozenset(),
    SessionStatus.FAILED: frozenset(),
    SessionStatus.ARCHIVED: frozenset(),
}


def _archivable_states() -> frozenset[SessionStatus]:
    """
    Every status except the running ones and ARCHIVED itself.
    Implements the "ANY (non-running) → ARCHIVED" rule.
    """
    return frozenset(
        s
        for s in SessionStatus
        if s not in RUNNING_STATES and s is not SessionStatus.ARCHIVED
    )


# Bolt the archive rule onto the map so validator.py has one flat structure
# to check, instead of special-casing ARCHIVED at call time.
for _state in _archivable_states():
    ALLOWED_TRANSITIONS[_state] = ALLOWED_TRANSITIONS[_state] | {
        SessionStatus.ARCHIVED
    }