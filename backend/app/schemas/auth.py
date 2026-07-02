"""
schemas/auth.py — Pydantic request/response schemas for auth endpoints.

Matches api-spec.md Section 2 exactly. These schemas are used by:
  - api/v1/auth.py  (route handlers)
  - dependencies/auth.py  (CurrentUser)
"""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, field_validator

# SRN regex pattern: PES<digit>UG<2 digits><2 uppercase letters><3 digits>
# Examples: PES2UG22CS001, PES1UG23EC047
_SRN_PATTERN = re.compile(r"^PES\dUG\d{2}[A-Z]{2}\d{3}$")


# ─────────────────────────────────────────────────────────────────────────────
# Request Schemas
# ─────────────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """POST /auth/login request body."""

    srn: str
    password: str

    @field_validator("srn", mode="before")
    @classmethod
    def validate_srn(cls, v: str) -> str:
        v = str(v).upper().strip()
        if not _SRN_PATTERN.match(v):
            raise ValueError(
                "SRN must match the format PES<digit>UG<2 digits><2 uppercase letters><3 digits> "
                "(e.g. PES2UG22CS001)"
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters.")
        return v


class RefreshRequest(BaseModel):
    """POST /auth/refresh request body."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """POST /auth/logout request body."""

    refresh_token: str


# ─────────────────────────────────────────────────────────────────────────────
# Response Schemas
# ─────────────────────────────────────────────────────────────────────────────

class UserInfo(BaseModel):
    """Embedded user object returned in login response."""

    user_id: str
    name: str
    srn: str
    team_id: Optional[str] = None


class LoginResponse(BaseModel):
    """Success payload inside data envelope for POST /auth/login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int           # seconds until access token expiry
    role: str
    user: UserInfo


class RefreshResponse(BaseModel):
    """Success payload inside data envelope for POST /auth/refresh."""

    access_token: str
    refresh_token: str
    expires_in: int


class MeResponse(BaseModel):
    """Success payload inside data envelope for GET /auth/me."""

    user_id: str
    name: str
    srn: str
    email: str
    role: str
    team_id: Optional[str] = None
    mentor_team_ids: list[str] = []


# ─────────────────────────────────────────────────────────────────────────────
# Internal — CurrentUser (used by dependency injector)
# ─────────────────────────────────────────────────────────────────────────────

class CurrentUser(BaseModel):
    """
    Decoded JWT claims attached to every authenticated request.

    This is NOT a MongoDB document — it is derived purely from the JWT payload.
    Services that need the full user document from MongoDB should call the user repo.
    """

    user_id: str
    role: str
    team_id: Optional[str] = None
    mentor_team_ids: list[str] = []

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    @property
    def is_mentor(self) -> bool:
        return self.role == "mentor"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
