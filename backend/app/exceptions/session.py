from .base import SessionException


class SessionNotFoundError(SessionException):
    """Raised when a requested team session does not exist."""

    def __init__(self):
        super().__init__(
            message="Team session not found.",
            status_code=404,
            error_code="SESSION_NOT_FOUND",
        )


class SessionAlreadyExistsError(SessionException):
    """Raised when attempting to create a session that already exists."""

    def __init__(self):
        super().__init__(
            message="Team session already exists.",
            status_code=409,
            error_code="SESSION_ALREADY_EXISTS",
        )


class ActiveSessionExistsError(SessionException):
    """Raised when an active session already exists for the team."""

    def __init__(self):
        super().__init__(
            message="An active team session already exists.",
            status_code=409,
            error_code="ACTIVE_SESSION_EXISTS",
        )


class InvalidStateTransitionError(SessionException):
    """Raised when an invalid session state transition is attempted."""

    def __init__(self):
        super().__init__(
            message="Invalid session state transition.",
            status_code=409,
            error_code="INVALID_STATE_TRANSITION",
        )


class FlowAlreadyRunningError(SessionException):
    """Raised when trying to start a workflow that is already running."""

    def __init__(self):
        super().__init__(
            message="Workflow is already running for this session.",
            status_code=409,
            error_code="FLOW_ALREADY_RUNNING",
        )


class CannotArchiveActiveSessionError(SessionException):
    """Raised when attempting to archive an active session."""

    def __init__(self):
        super().__init__(
            message="Cannot archive an active session.",
            status_code=409,
            error_code="CANNOT_ARCHIVE_ACTIVE_SESSION",
        )