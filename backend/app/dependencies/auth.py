"""
dependencies/auth.py — FastAPI dependency injectors for authentication and authorization.

Two core dependencies:
  1. get_current_user       — Validates JWT, returns CurrentUser. Used on all protected routes.
  2. require_role(roles)    — Factory that returns a dependency enforcing role membership.

CurrentUser is a simple Pydantic model carrying the decoded JWT claims. It is NOT
fetched from MongoDB on every request — the JWT is the source of truth for basic
identity. MongoDB is only hit when the full user document is explicitly needed.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import decode_token
from app.core.constants import UserRole
from app.exceptions.base import InsufficientPermissionsError
from app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

# HTTPBearer extracts "Bearer <token>" from the Authorization header.
# auto_error=False means we handle the missing-token case ourselves for a cleaner error.
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> CurrentUser:
    """
    FastAPI dependency: validate the Bearer JWT and return the current user.

    Raises:
        TokenInvalidError  (401) — missing or malformed token.
        TokenExpiredError  (401) — token has expired.

    Usage:
        @router.get("/me")
        async def me(user: CurrentUser = Depends(get_current_user)):
            ...
    """
    from app.exceptions.base import TokenInvalidError  # local import avoids circular

    if credentials is None:
        raise TokenInvalidError("Authorization header is missing. Provide a Bearer token.")

    payload = decode_token(credentials.credentials)  # raises TokenExpiredError or TokenInvalidError

    return CurrentUser(
        user_id=payload["sub"],
        role=payload.get("role", ""),
        team_id=payload.get("team_id"),
        mentor_team_ids=payload.get("mentor_team_ids", []),
    )


def require_role(*roles: str):
    """
    Dependency factory: allow only users whose role is in `roles`.

    Usage:
        @router.post("/sessions")
        async def create_session(user = Depends(require_role(UserRole.STUDENT))):
            ...
    """
    allowed = set(roles)

    async def _check_role(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if current_user.role not in allowed:
            logger.info(
                "Role check failed: user_id=%s role=%s required=%s",
                current_user.user_id,
                current_user.role,
                allowed,
            )
            raise InsufficientPermissionsError(
                f"This endpoint requires one of these roles: {', '.join(sorted(allowed))}."
            )
        return current_user

    return _check_role


# ── Convenience role dependencies (re-exported for import ergonomics) ──────────

def require_student():
    return require_role(UserRole.STUDENT)

def require_mentor():
    return require_role(UserRole.MENTOR)

def require_admin():
    return require_role(UserRole.ADMIN)

def require_student_or_admin():
    return require_role(UserRole.STUDENT, UserRole.ADMIN)

def require_mentor_or_admin():
    return require_role(UserRole.MENTOR, UserRole.ADMIN)

def require_any_authenticated():
    return require_role(UserRole.STUDENT, UserRole.MENTOR, UserRole.ADMIN)
