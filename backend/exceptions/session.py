"""
exceptions/session.py — Re-exports session-scoped exceptions from base.py.

All exception classes are defined in exceptions/base.py (single source of truth).
This module exists purely for ergonomic imports:

    from exceptions.session import SessionNotFoundError
    # vs
    from exceptions.base import SessionNotFoundError

Both forms work identically.
"""

from exceptions.base import (  # noqa: F401
    ActiveSessionExistsError,
    CannotArchiveActiveSessionError,
    DFVNotUnlockedError,
    FlowAlreadyRunningError,
    InvalidStateTransitionError,
    SessionAlreadyExistsError,
    SessionNotFoundError,
)
