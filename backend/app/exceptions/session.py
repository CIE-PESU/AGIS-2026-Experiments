"""
exceptions/session.py — Re-exports session-scoped exceptions from base.py.

All exception classes are defined in exceptions/base.py (single source of truth).
This module exists purely for ergonomic imports:

    from app.exceptions.session import SessionNotFoundError
    # vs
    from app.exceptions.base import SessionNotFoundError

Both forms work identically.
"""

from app.exceptions.base import (  # noqa: F401
    SessionNotFoundError,
    SessionAlreadyExistsError,
    ActiveSessionExistsError,
    InvalidStateTransitionError,
    FlowAlreadyRunningError,
    DFVNotUnlockedError,
    CannotArchiveActiveSessionError,
)