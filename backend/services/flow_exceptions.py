"""
Exceptions raised by FlowService.

Same situation as state_machine/exceptions.py on Day 1: most of these
already exist in Parthiv's exception hierarchy (exceptions/base.py, B-07)
and are duplicated here on purpose so this branch has zero import-order
dependency on his branch landing first.

Reconciliation needed at merge time:
  - SessionNotFoundError        -> already in Parthiv's SessionException tree, dedupe.
  - FlowAlreadyRunningError     -> already in Parthiv's SessionException tree, dedupe.
  - InvalidStateTransitionError -> already in Parthiv's SessionException tree, AND
    already duplicated once in state_machine/exceptions.py (see that file's note).
    That's now two duplicates of the same name across two of my own branches —
    worth collapsing to one shared definition when B-05 and B-12 both merge.
  - KafkaUnavailableError       -> already in Parthiv's KafkaException tree, dedupe.
  - DFVNotUnlockedError         -> NOT in Parthiv's documented hierarchy
    (backend-arch.md Section 14.1 doesn't list it, though api-spec.md
    Section 4.2 and the error catalog both require DFV_NOT_UNLOCKED / 409).
    This one genuinely needs to be *added* to exceptions/base.py, not just
    deduped — flag it in the PR.
  - SessionUpdateConflictError  -> NOT in the error catalog at all yet
    (api-spec.md Section 11). Needed for the optimistic-lock case
    (update_status returns False). Using SESSION_VERSION_CONFLICT / 409
    as a placeholder code — flag this as a spec gap, it's the same issue
    Bhavesh's E4 edge case (Day 4) will need to test against.
"""

from __future__ import annotations


from exceptions.base import AppException

class FlowServiceError(AppException):
    """Base class for this module's exceptions. Now inherits from AppException."""

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
            f"Session '{session_id}' already has a flow running "
            f"(status: {current_status})"
        )


class InvalidStateTransitionError(FlowServiceError):
    error_code = "INVALID_STATE_TRANSITION"
    http_status = 409

    def __init__(self, current_status, target_status):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Cannot transition from '{current_status}' to '{target_status}'"
        )


class DFVNotUnlockedError(FlowServiceError):
    error_code = "DFV_NOT_UNLOCKED"
    http_status = 409

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(
            f"Session '{session_id}' has not passed TIPSC's ready_for_dfv gate"
        )


class KafkaUnavailableError(FlowServiceError):
    error_code = "KAFKA_UNAVAILABLE"
    http_status = 503

    def __init__(self, flow: str):
        self.flow = flow
        super().__init__(f"Kafka publish failed after retries for flow '{flow}'")


class SessionUpdateConflictError(FlowServiceError):
    error_code = "SESSION_VERSION_CONFLICT"  # placeholder — not yet in error catalog
    http_status = 409

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(
            f"Session '{session_id}' was modified concurrently "
            "(optimistic lock version mismatch)"
        )