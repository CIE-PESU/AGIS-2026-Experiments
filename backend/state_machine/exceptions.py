"""Pure transition errors translated by FlowService into shared API errors."""

from state_machine.states import SessionStatus


class InvalidStateTransitionError(Exception):
    """Raised when a transition isn't allowed by ALLOWED_TRANSITIONS."""

    def __init__(self, current_status: SessionStatus, target_status: SessionStatus):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Cannot transition session from '{current_status.value}' to '{target_status.value}'"
        )
