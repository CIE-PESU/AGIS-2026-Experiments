"""
auth/jwt.py — JWT creation, refresh token generation, and token decoding.

Access Token (JWT):
  - Signed with HS256 using JWT_SECRET from config
  - Payload: user_id, role, team_id, mentor_team_ids, exp, iat, jti
  - Expires in JWT_EXPIRY_MINUTES (default 15 min)
  - exp claim is ALWAYS present and ALWAYS checked

Refresh Token:
  - Opaque UUID4 string returned raw to the client
  - Stored in MongoDB as bcrypt hash with TTL index
  - Never carries any user claims — lookup is by hash

Token Decoding:
  - Always validates signature and exp
  - Raises TokenExpiredError for expired tokens
  - Raises TokenInvalidError for malformed / tampered tokens
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.exceptions.base import TokenExpiredError, TokenInvalidError

logger = logging.getLogger(__name__)

# Bcrypt context for hashing refresh tokens
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Access Token
# ─────────────────────────────────────────────────────────────────────────────

def create_access_token(
    user_id: str,
    role: str,
    team_id: str | None = None,
    mentor_team_ids: list[str] | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        user_id: The user's unique ID (stored in MongoDB as _id or a prefixed string).
        role: One of "student", "mentor", "admin".
        team_id: The student's team ID (None for non-students).
        mentor_team_ids: List of team IDs the mentor supervises (None for non-mentors).

    Returns:
        A signed JWT string valid for JWT_EXPIRY_MINUTES minutes.
    """
    now = _utc_now()
    expire = now + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)

    payload: dict[str, Any] = {
        "sub": user_id,                        # Subject (user ID)
        "role": role,
        "team_id": team_id,
        "mentor_team_ids": mentor_team_ids or [],
        "iat": now,                            # Issued-at
        "exp": expire,                         # Expiry — ALWAYS present
        "jti": str(uuid.uuid4()),              # JWT ID — unique per token
    }

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    logger.debug("Access token created for user_id=%s role=%s exp=%s", user_id, role, expire.isoformat())
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
    raw = str(uuid.uuid4())
    hashed = _pwd_context.hash(raw)
    return raw, hashed


def verify_refresh_token(raw_token: str, stored_hash: str) -> bool:
    """
    Verify a raw refresh token against its stored bcrypt hash.

    Args:
        raw_token: The token value received from the client.
        stored_hash: The bcrypt hash retrieved from MongoDB.

    Returns:
        True if the token matches, False otherwise.
    """
    return _pwd_context.verify(raw_token, stored_hash)


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
            options={"require_exp": True},    # exp MUST be present
        )
    except ExpiredSignatureError as exc:
        logger.info("Expired JWT received")
        raise TokenExpiredError() from exc
    except JWTError as exc:
        logger.warning("Invalid JWT | %s", str(exc))
        raise TokenInvalidError() from exc

    # Extra safety: sub must be present
    if not payload.get("sub"):
        raise TokenInvalidError("Token is missing the subject (sub) claim.")

    return payload
