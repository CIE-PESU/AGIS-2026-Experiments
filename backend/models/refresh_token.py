"""
models/refresh_token.py — Beanie ODM model for the refresh_tokens collection.

Stores hashed refresh tokens with a TTL index on expires_at.
The raw token is NEVER stored — only the bcrypt hash.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from beanie import Document
from pydantic import Field


class RefreshToken(Document):
    """
    A single refresh token record.

    Fields:
        token_hash  : bcrypt hash of the opaque UUID4 refresh token.
        user_id     : Owner of this token.
        expires_at  : UTC datetime when this token expires (7-day TTL).
        revoked     : If True, this token has been explicitly invalidated (logout).
        created_at  : Creation timestamp.
    """

    token_hash: str
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None
    expires_at: datetime
    revoked: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "refresh_tokens"
        indexes = [
            # Unique index on token_hash — each hash is stored once
            [("token_hash", 1)],
            [("workspace_id", 1)],
        ]

    @classmethod
    def create_for_user(cls, user_id: str, token_hash: str, expiry_days: int = 7, workspace_id: str | None = None) -> "RefreshToken":
        """Factory method to build a new RefreshToken for a given user."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)
        return cls(
            token_hash=token_hash,
            user_id=user_id,
            workspace_id=workspace_id,
            expires_at=expires_at,
        )

    @classmethod
    def create_for_workspace(cls, workspace_id: str, token_hash: str, expiry_days: int = 7) -> "RefreshToken":
        """Factory method to build a new RefreshToken for a guest workspace."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)
        return cls(
            token_hash=token_hash,
            workspace_id=workspace_id,
            expires_at=expires_at,
        )

    @property
    def is_expired(self) -> bool:
        expires = self.expires_at
        # MongoDB may return naive datetimes — treat them as UTC
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires

    @property
    def is_valid(self) -> bool:
        return not self.revoked and not self.is_expired
