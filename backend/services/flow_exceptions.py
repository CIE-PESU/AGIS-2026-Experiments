"""Flow trigger errors with run context and stable API error codes.

These constructors retain the flow service's session-id and flow-name arguments.
All errors inherit AppException and use the standard API error envelope.
"""

from __future__ import annotations

from exceptions.base import AppException


class FlowServiceError(AppException):
    """Base class for flow trigger errors."""

    error_code: str = "FLOW_SERVICE_ERROR"
    http_status: int = 500

    def __init__(self, message: str):
        super().__init__(message)


class SessionNotFoundError(FlowServiceError):
    error_code = "SESSION_NOT_FOUND"
    http_status = 404

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"No session found with id '{session_id}'")


class FlowAlreadyRunningError(FlowServiceError):
    error_code = "FLOW_ALREADY_RUNNING"
    http_status = 409

    def __init__(self, session_id: str, current_status: str):
        self.session_id = session_id
        self.current_status = current_status
        super().__init__(
            f"Session '{session_id}' already has a flow running (status: {current_status})"
        )


class InvalidStateTransitionError(FlowServiceError):
    error_code = "INVALID_STATE_TRANSITION"
    http_status = 409

    def __init__(self, current_status, target_status):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(f"Cannot transition from '{current_status}' to '{target_status}'")


class DFVNotUnlockedError(FlowServiceError):
    error_code = "DFV_NOT_UNLOCKED"
    http_status = 409

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session '{session_id}' has not passed TIPSC's ready_for_dfv gate")


class KafkaUnavailableError(FlowServiceError):
    error_code = "KAFKA_UNAVAILABLE"
    http_status = 503

    def __init__(self, flow: str):
        self.flow = flow
        super().__init__(f"Kafka publish failed after retries for flow '{flow}'")


class SessionUpdateConflictError(FlowServiceError):
    error_code = "SESSION_VERSION_CONFLICT"
    http_status = 409

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(
            f"Session '{session_id}' was modified concurrently (optimistic lock version mismatch)"
        )
