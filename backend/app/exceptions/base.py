"""
Base exception hierarchy for the AGIS Backend.

Every custom exception in the project inherits from AppException.
"""


class AppException(Exception):
    """
    Base class for all application exceptions.
    """

    def __init__(
        self,
        message: str,
        status_code: int,
        error_code: str,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


# ==========================================================
# AUTH BASE EXCEPTION
# ==========================================================

class AuthException(AppException):
    """Base class for all authentication and authorization exceptions."""

    def __init__(
        self,
        message: str,
        status_code: int,
        error_code: str,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
        )


# ==========================================================
# SESSION BASE EXCEPTION
# ==========================================================

class SessionException(AppException):
    """Base class for all Team Session related exceptions."""

    def __init__(
        self,
        message: str,
        status_code: int,
        error_code: str,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
        )


# ==========================================================
# KAFKA BASE EXCEPTION
# ==========================================================

class KafkaException(AppException):
    """Base class for all Kafka related exceptions."""

    def __init__(
        self,
        message: str,
        status_code: int,
        error_code: str,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
        )


# ==========================================================
# DATABASE BASE EXCEPTION
# ==========================================================

class DatabaseException(AppException):
    """Base class for all database related exceptions."""

    def __init__(
        self,
        message: str,
        status_code: int,
        error_code: str,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
        )


class DatabaseUnavailableError(DatabaseException):
    """Raised when the database service is unavailable."""

    def __init__(self):
        super().__init__(
            message="Database service is unavailable.",
            status_code=503,
            error_code="DATABASE_UNAVAILABLE",
        )


class DocumentNotFoundError(DatabaseException):
    """Raised when a requested document is not found."""

    def __init__(self):
        super().__init__(
            message="Requested document was not found.",
            status_code=404,
            error_code="DOCUMENT_NOT_FOUND",
        )


# ==========================================================
# VALIDATION EXCEPTION
# ==========================================================

class ValidationException(AppException):
    """Raised when request validation fails."""

    def __init__(
        self,
        message: str = "Validation failed.",
        error_code: str = "VALIDATION_ERROR",
    ):
        super().__init__(
            message=message,
            status_code=422,
            error_code=error_code,
        )