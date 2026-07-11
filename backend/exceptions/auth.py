from .base import AuthException


class InvalidCredentialsError(AuthException):
    """Raised when username/email or password is incorrect."""

    def __init__(self):
        super().__init__(
            message="Invalid username or password.",
            status_code=401,
            error_code="INVALID_CREDENTIALS",
        )


class TokenExpiredError(AuthException):
    """Raised when the access token has expired."""

    def __init__(self):
        super().__init__(
            message="Access token has expired.",
            status_code=401,
            error_code="TOKEN_EXPIRED",
        )


class TokenInvalidError(AuthException):
    """Raised when the provided JWT token is invalid."""

    def __init__(self):
        super().__init__(
            message="Invalid access token.",
            status_code=401,
            error_code="TOKEN_INVALID",
        )


class RefreshTokenInvalidError(AuthException):
    """Raised when the refresh token is invalid or revoked."""

    def __init__(self):
        super().__init__(
            message="Invalid refresh token.",
            status_code=401,
            error_code="REFRESH_TOKEN_INVALID",
        )


class InsufficientPermissionsError(AuthException):
    """Raised when the user does not have permission to perform an action."""

    def __init__(self):
        super().__init__(
            message="You do not have permission to perform this action.",
            status_code=403,
            error_code="INSUFFICIENT_PERMISSIONS",
        )