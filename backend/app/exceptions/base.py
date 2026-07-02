"""
exceptions/base.py — Full typed exception hierarchy for the AGIS backend.

Every exception class maps directly to an HTTP status code and an error catalog
code (defined in api-spec.md Section 11). Global handlers in exceptions/handlers.py
convert these into the standard error envelope.

Hierarchy:
    AppException
    ├── AuthException
    │   ├── InvalidCredentialsError       (401  INVALID_CREDENTIALS)
    │   ├── TokenExpiredError             (401  TOKEN_EXPIRED)
    │   ├── TokenInvalidError             (401  TOKEN_INVALID)
    │   ├── RefreshTokenInvalidError      (401  REFRESH_TOKEN_INVALID)
    │   ├── RefreshTokenExpiredError      (401  REFRESH_TOKEN_EXPIRED)
    │   └── InsufficientPermissionsError  (403  INSUFFICIENT_PERMISSIONS)
    ├── SessionException
    │   ├── SessionNotFoundError          (404  SESSION_NOT_FOUND)
    │   ├── SessionAlreadyExistsError     (409  SESSION_ALREADY_EXISTS)
    │   ├── ActiveSessionExistsError      (409  ACTIVE_SESSION_EXISTS)
    │   ├── InvalidStateTransitionError   (409  INVALID_STATE_TRANSITION)
    │   ├── FlowAlreadyRunningError       (409  FLOW_ALREADY_RUNNING)
    │   ├── DFVNotUnlockedError           (409  DFV_NOT_UNLOCKED)
    │   └── CannotArchiveActiveSessionError (409 CANNOT_ARCHIVE_ACTIVE_SESSION)
    ├── CommentException
    │   └── CommentNotFoundError          (404  COMMENT_NOT_FOUND)
    ├── WorkerException
    │   ├── InvalidWorkerSecretError      (403  INVALID_WORKER_SECRET)
    │   ├── InvalidOutputSchemaError      (400  INVALID_OUTPUT_SCHEMA)
    │   └── CorrelationIDMismatchError    (409  CORRELATION_ID_MISMATCH)
    ├── KafkaException
    │   ├── KafkaPublishError             (503  KAFKA_UNAVAILABLE)
    │   └── KafkaUnavailableError         (503  KAFKA_UNAVAILABLE)
    ├── DatabaseException
    │   ├── DatabaseUnavailableError      (503  DATABASE_UNAVAILABLE)
    │   └── DocumentNotFoundError         (404  SESSION_NOT_FOUND)
    ├── PESAuthException
    │   ├── PESAuthUnavailableError       (503  PES_AUTH_UNAVAILABLE)
    │   └── InvalidCredentialsError       → re-exported above
    └── ValidationException               (422  VALIDATION_ERROR)
"""

from __future__ import annotations

from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────────────────────

class AppException(Exception):
    """
    Root exception for the AGIS backend.

    Every subclass MUST declare:
      - http_status  : int  — The HTTP response status code.
      - error_code   : str  — Catalog code from api-spec.md Section 11.
    """

    http_status: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "", field: str | None = None, detail: Any = None) -> None:
        super().__init__(message)
        self.message = message or self.__class__.__name__
        self.field = field          # Optional: which field caused the error (for 422)
        self.detail = detail        # Optional: extra structured info (not exposed in production)


# ─────────────────────────────────────────────────────────────────────────────
# Auth Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class AuthException(AppException):
    """Base for all authentication / authorization errors."""


class InvalidCredentialsError(AuthException):
    http_status = 401
    error_code = "INVALID_CREDENTIALS"

    def __init__(self, message: str = "Invalid SRN or password.") -> None:
        super().__init__(message)


class TokenExpiredError(AuthException):
    http_status = 401
    error_code = "TOKEN_EXPIRED"

    def __init__(self, message: str = "Access token has expired.") -> None:
        super().__init__(message)


class TokenInvalidError(AuthException):
    http_status = 401
    error_code = "TOKEN_INVALID"

    def __init__(self, message: str = "Token is malformed or signature is invalid.") -> None:
        super().__init__(message)


class RefreshTokenInvalidError(AuthException):
    http_status = 401
    error_code = "REFRESH_TOKEN_INVALID"

    def __init__(self, message: str = "Refresh token not found or has been tampered with.") -> None:
        super().__init__(message)


class RefreshTokenExpiredError(AuthException):
    http_status = 401
    error_code = "REFRESH_TOKEN_EXPIRED"

    def __init__(self, message: str = "Refresh token has expired. Please log in again.") -> None:
        super().__init__(message)


class InsufficientPermissionsError(AuthException):
    http_status = 403
    error_code = "INSUFFICIENT_PERMISSIONS"

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message)


# ─────────────────────────────────────────────────────────────────────────────
# Session Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class SessionException(AppException):
    """Base for all session-related errors."""


class SessionNotFoundError(SessionException):
    http_status = 404
    error_code = "SESSION_NOT_FOUND"

    def __init__(self, message: str = "No session found with the given ID.") -> None:
        super().__init__(message)


class SessionAlreadyExistsError(SessionException):
    http_status = 409
    error_code = "SESSION_ALREADY_EXISTS"

    def __init__(self, message: str = "A session with this idempotency key already exists.") -> None:
        super().__init__(message)


class ActiveSessionExistsError(SessionException):
    http_status = 409
    error_code = "ACTIVE_SESSION_EXISTS"

    def __init__(self, message: str = "You already have an active session. Archive it before creating a new one.") -> None:
        super().__init__(message)


class InvalidStateTransitionError(SessionException):
    http_status = 409
    error_code = "INVALID_STATE_TRANSITION"

    def __init__(
        self,
        current_status: str = "",
        target_status: str = "",
        message: str = "",
    ) -> None:
        msg = message or f"Cannot transition from '{current_status}' to '{target_status}'."
        super().__init__(msg)
        self.current_status = current_status
        self.target_status = target_status


class FlowAlreadyRunningError(SessionException):
    http_status = 409
    error_code = "FLOW_ALREADY_RUNNING"

    def __init__(self, message: str = "A flow is already running on this session.") -> None:
        super().__init__(message)


class DFVNotUnlockedError(SessionException):
    http_status = 409
    error_code = "DFV_NOT_UNLOCKED"

    def __init__(self, message: str = "TIPSC evaluation did not pass ready_for_dfv. Review TIPSC output before proceeding.") -> None:
        super().__init__(message)


class CannotArchiveActiveSessionError(SessionException):
    http_status = 409
    error_code = "CANNOT_ARCHIVE_ACTIVE_SESSION"

    def __init__(self, message: str = "Cannot archive a session while a flow is currently running.") -> None:
        super().__init__(message)


# ─────────────────────────────────────────────────────────────────────────────
# Comment Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class CommentException(AppException):
    """Base for comment-related errors."""


class CommentNotFoundError(CommentException):
    http_status = 404
    error_code = "COMMENT_NOT_FOUND"

    def __init__(self, message: str = "No comment found with the given ID.") -> None:
        super().__init__(message)


# ─────────────────────────────────────────────────────────────────────────────
# Worker Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class WorkerException(AppException):
    """Base for internal worker callback errors."""


class InvalidWorkerSecretError(WorkerException):
    http_status = 403
    error_code = "INVALID_WORKER_SECRET"

    def __init__(self, message: str = "Worker secret is missing or invalid.") -> None:
        super().__init__(message)


class InvalidOutputSchemaError(WorkerException):
    http_status = 400
    error_code = "INVALID_OUTPUT_SCHEMA"

    def __init__(self, message: str = "Worker output is missing required fields.") -> None:
        super().__init__(message)


class CorrelationIDMismatchError(WorkerException):
    http_status = 409
    error_code = "CORRELATION_ID_MISMATCH"

    def __init__(self, message: str = "Correlation ID does not match the published event.") -> None:
        super().__init__(message)


# ─────────────────────────────────────────────────────────────────────────────
# Kafka Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class KafkaException(AppException):
    """Base for Kafka-related errors."""


class KafkaPublishError(KafkaException):
    http_status = 503
    error_code = "KAFKA_UNAVAILABLE"

    def __init__(self, message: str = "Failed to publish event to Kafka after retries.") -> None:
        super().__init__(message)


class KafkaUnavailableError(KafkaException):
    http_status = 503
    error_code = "KAFKA_UNAVAILABLE"

    def __init__(self, message: str = "Kafka producer is not available.") -> None:
        super().__init__(message)


# ─────────────────────────────────────────────────────────────────────────────
# Database Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class DatabaseException(AppException):
    """Base for database-related errors."""


class DatabaseUnavailableError(DatabaseException):
    http_status = 503
    error_code = "DATABASE_UNAVAILABLE"

    def __init__(self, message: str = "Database is currently unavailable.") -> None:
        super().__init__(message)


class DocumentNotFoundError(DatabaseException):
    http_status = 404
    error_code = "SESSION_NOT_FOUND"

    def __init__(self, message: str = "Requested document not found.") -> None:
        super().__init__(message)


# ─────────────────────────────────────────────────────────────────────────────
# PES Auth Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class PESAuthException(AppException):
    """Base for PES Auth integration errors."""


class PESAuthUnavailableError(PESAuthException):
    http_status = 503
    error_code = "PES_AUTH_UNAVAILABLE"

    def __init__(self, message: str = "PES Auth API is unavailable or timed out.") -> None:
        super().__init__(message)


# ─────────────────────────────────────────────────────────────────────────────
# Validation Exception
# ─────────────────────────────────────────────────────────────────────────────

class ValidationException(AppException):
    http_status = 422
    error_code = "VALIDATION_ERROR"

    def __init__(self, message: str = "Request validation failed.", field: str | None = None) -> None:
        super().__init__(message, field=field)
