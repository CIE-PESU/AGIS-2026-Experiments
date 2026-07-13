"""
models/refresh_token.py — Beanie ODM model for the refresh_tokens collection.

Stores hashed refresh tokens with a TTL index on expires_at.
The raw token is NEVER stored — only the bcrypt hash.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
    user_id: str
    expires_at: datetime
    revoked: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "refresh_tokens"
        indexes = [
            # Unique index on token_hash — each hash is stored once
            [("token_hash", 1)],
            # TTL index: MongoDB auto-deletes expired documents
            # (the 'expireAfterSeconds=0' means expire at the expires_at value itself)
        ]

    @classmethod
    def create_for_user(cls, user_id: str, token_hash: str, expiry_days: int = 7) -> "RefreshToken":
        """Factory method to build a new RefreshToken for a given user."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)
        return cls(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
        )

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.revoked and not self.is_expired
