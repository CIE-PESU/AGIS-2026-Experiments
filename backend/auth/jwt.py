"""
auth/jwt.py — JWT creation, refresh token generation, and token decoding.

Access Token (JWT):
  - Signed with HS256 using JWT_SECRET from config
  - Payload: user_id, role, team_id, mentor_team_ids, exp, iat, jti
  - Expires in JWT_EXPIRY_MINUTES (default 15 min)
  - exp claim is ALWAYS present and ALWAYS checked

Refresh Token:
  - Opaque high-entropy string returned raw to the client
  - Stored in MongoDB as SHA-256 digest with TTL index
  - Never carries any user claims — lookup is by hash

Token Decoding:
  - Always validates signature and exp
  - Raises TokenExpiredError for expired tokens
  - Raises TokenInvalidError for malformed / tampered tokens
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from core.config import settings
from exceptions.base import TokenExpiredError, TokenInvalidError

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _utc_now() -> datetime:
    return datetime.now(UTC)


# ─────────────────────────────────────────────────────────────────────────────
# Access Token
# ─────────────────────────────────────────────────────────────────────────────


def create_access_token(
    user_id: str,
    role: str,
    name: str,
    team_id: str | None = None,
    mentor_team_ids: list[str] | None = None,
    workspace_id: str | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        user_id: The user's unique ID (stored in MongoDB as _id or a prefixed string).
        role: One of "student", "mentor", "admin", "mentor_workspace".
        name: The user's name.
        team_id: The student's team ID (None for non-students).
        mentor_team_ids: List of team IDs the mentor supervises (None for non-mentors).
        workspace_id: Workspace ID associated with this user session.

    Returns:
        A signed JWT string valid for JWT_EXPIRY_MINUTES minutes.
    """
    now = _utc_now()
    expire = now + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)

    payload: dict[str, Any] = {
        "sub": user_id,  # Subject (user ID)
        "role": role,
        "name": name,
        "team_id": team_id,
        "workspace_id": workspace_id,
        "mentor_team_ids": mentor_team_ids or [],
        "iat": now,  # Issued-at
        "exp": expire,  # Expiry — ALWAYS present
        "jti": str(uuid.uuid4()),  # JWT ID — unique per token
    }

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    logger.debug(
        "Access token created for user_id=%s role=%s exp=%s", user_id, role, expire.isoformat()
    )
    return token


# ─────────────────────────────────────────────────────────────────────────────
# Refresh Token
# ─────────────────────────────────────────────────────────────────────────────


def create_refresh_token() -> tuple[str, str]:
    """
    Generate an opaque refresh token.

    Returns:
        A tuple of (raw_token, hashed_token).
        - raw_token    → sent to the client.
        - hashed_token → stored in MongoDB refresh_tokens collection.
    """
    raw = secrets.token_urlsafe(48)
    return raw, refresh_token_digest(raw)


def refresh_token_digest(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def verify_refresh_token(raw_token: str, stored_hash: str) -> bool:
    return hmac.compare_digest(refresh_token_digest(raw_token), stored_hash)


# ─────────────────────────────────────────────────────────────────────────────
# Token Decoding
# ─────────────────────────────────────────────────────────────────────────────


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Validates:
      - Signature (JWT_SECRET + HS256)
      - exp claim (must be present and in the future)

    Args:
        token: The raw JWT string from the Authorization header.

    Returns:
        The decoded payload dict containing sub, role, team_id, mentor_team_ids, etc.

    Raises:
        TokenExpiredError: Token's exp is in the past.
        TokenInvalidError: Token is malformed, signature mismatch, or missing exp.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "iat", "jti"]},  # exp MUST be present
        )
    except ExpiredSignatureError as exc:
        logger.info("Expired JWT received")
        raise TokenExpiredError() from exc
    except InvalidTokenError as exc:
        logger.warning("Invalid JWT | %s", str(exc))
        raise TokenInvalidError() from exc

    # Extra safety: sub must be present
    if not payload.get("sub"):
        raise TokenInvalidError("Token is missing the subject (sub) claim.")

    return payload
