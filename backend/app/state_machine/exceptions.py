"""
Exception raised by the state machine.

NOTE for integration (Parthiv's B-07 branch): the plan's exception hierarchy
(exceptions/base.py) also defines `InvalidStateTransitionError` under
`SessionException`, mapped to 409. Rather than importing across branches on
Day 1 and creating a merge-order dependency, this module defines its own
version so state_machine/ stays pure logic with zero imports outside itself.

When both branches land on develop/backend, either:
  (a) make this class inherit from app.exceptions.base.SessionException, or
  (b) catch this in the service layer and re-raise the shared one.
Whichever Palash/Parthiv prefer for the exception hierarchy — flag it in
the PR so we don't end up with two InvalidStateTransitionError classes
floating around long-term.
"""

from app.state_machine.states import SessionStatus


class InvalidStateTransitionError(Exception):
    """Raised when a transition isn't allowed by ALLOWED_TRANSITIONS."""

    def __init__(self, current_status: SessionStatus, target_status: SessionStatus):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Cannot transition session from '{current_status.value}' "
            f"to '{target_status.value}'"
        )