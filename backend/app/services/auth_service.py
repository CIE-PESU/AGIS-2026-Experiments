"""
services/auth_service.py — Business logic for authentication flows.

Responsibilities:
  - Coordinate with PES Auth client to validate credentials
  - Upsert user in MongoDB after successful PES validation
  - Create access + refresh tokens
  - Handle refresh token rotation
  - Handle logout (revoke refresh token)

This service is the ONLY place that issues tokens.
Route handlers call this — they never touch jwt.py or pes_client.py directly.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.auth.jwt import create_access_token, create_refresh_token, verify_refresh_token
from app.auth.pes_client import pes_auth_client
from app.core.config import settings
from app.core.constants import AuditEvent
from app.exceptions.base import RefreshTokenExpiredError, RefreshTokenInvalidError
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginResponse, MeResponse, RefreshResponse, UserInfo

logger = logging.getLogger(__name__)


class AuthService:
    """Handles all authentication and token management operations."""

    # ── Login ──────────────────────────────────────────────────────────────────

    async def login(self, srn: str, password: str) -> LoginResponse:
        """
        Authenticate a user via PES Auth and return JWT tokens.

        Steps:
          1. Validate credentials against PES Auth API (raises on failure)
          2. Upsert user document in MongoDB
          3. Generate access token (JWT) + refresh token (opaque UUID4)
          4. Store refresh token hash in MongoDB
          5. Return token response

        Raises:
            InvalidCredentialsError  : PES returned 401
            PESAuthUnavailableError  : PES timed out or is down
        """
        # Step 1: Validate via PES
        pes_data = await pes_auth_client.validate_credentials(srn=srn, password=password)

        # Step 2: Upsert user in MongoDB
        user = await self._upsert_user(pes_data)

        # Step 3: Generate tokens
        access_token = create_access_token(
            user_id=str(user.id),
            role=user.role,
            team_id=user.team_id,
            mentor_team_ids=user.mentor_team_ids,
        )
        raw_refresh, hashed_refresh = create_refresh_token()

        # Step 4: Store hashed refresh token
        token_doc = RefreshToken.create_for_user(
            user_id=str(user.id),
            token_hash=hashed_refresh,
            expiry_days=settings.REFRESH_TOKEN_EXPIRY_DAYS,
        )
        await token_doc.insert()

        logger.info("Login successful: user_id=%s role=%s", user.id, user.role)

        return LoginResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.JWT_EXPIRY_MINUTES * 60,
            role=user.role,
            user=UserInfo(
                user_id=str(user.id),
                name=user.name,
                srn=user.srn,
                team_id=user.team_id,
            ),
        )

    # ── Refresh ────────────────────────────────────────────────────────────────

    async def refresh_tokens(self, raw_refresh_token: str) -> RefreshResponse:
        """
        Exchange a valid refresh token for new access + refresh tokens (rotation).

        Old refresh token is revoked immediately after finding it.

        Raises:
            RefreshTokenInvalidError : Token not found or tampered.
            RefreshTokenExpiredError : Token TTL has elapsed.
        """
        # Find all non-revoked tokens for matching (we must verify hash)
        # We load recent un-revoked tokens and check via bcrypt.
        # NOTE: This is O(n) over recent tokens; acceptable for this scale.
        # Production optimisation: store a secondary lookup index (partial hash).
        token_doc = await self._find_refresh_token(raw_refresh_token)

        if token_doc.is_expired:
            await token_doc.set({RefreshToken.revoked: True})
            raise RefreshTokenExpiredError()

        # Revoke the old token immediately (token rotation)
        await token_doc.set({RefreshToken.revoked: True})

        # Load the user to re-issue token with current claims
        user = await User.get(token_doc.user_id)
        if user is None:
            raise RefreshTokenInvalidError("User associated with this token no longer exists.")

        # Issue new tokens
        access_token = create_access_token(
            user_id=str(user.id),
            role=user.role,
            team_id=user.team_id,
            mentor_team_ids=user.mentor_team_ids,
        )
        raw_refresh, hashed_refresh = create_refresh_token()
        new_token_doc = RefreshToken.create_for_user(
            user_id=str(user.id),
            token_hash=hashed_refresh,
            expiry_days=settings.REFRESH_TOKEN_EXPIRY_DAYS,
        )
        await new_token_doc.insert()

        logger.info("Token refreshed for user_id=%s", user.id)

        return RefreshResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.JWT_EXPIRY_MINUTES * 60,
        )

    # ── Logout ─────────────────────────────────────────────────────────────────

    async def logout(self, raw_refresh_token: str) -> None:
        """
        Revoke a refresh token server-side.

        The access token continues to work until its exp — this is acceptable
        given the 15-minute TTL. The client is responsible for discarding both tokens.

        Raises:
            RefreshTokenInvalidError : Token not found (idempotent — does not raise if already revoked).
        """
        try:
            token_doc = await self._find_refresh_token(raw_refresh_token)
            if not token_doc.revoked:
                await token_doc.set({RefreshToken.revoked: True})
                logger.info("Logout: revoked token for user_id=%s", token_doc.user_id)
        except RefreshTokenInvalidError:
            # Idempotent: logout with an already-invalid token is not an error.
            logger.info("Logout called with already-invalid token (idempotent)")

    # ── Get Me ─────────────────────────────────────────────────────────────────

    async def get_current_user_profile(self, user_id: str) -> MeResponse:
        """
        Load the full user profile from MongoDB by user_id.

        Raises:
            SessionNotFoundError (via DocumentNotFoundError): User not in DB.
        """
        from app.exceptions.base import TokenInvalidError

        user = await User.get(user_id)
        if user is None:
            raise TokenInvalidError("User profile not found. Please log in again.")

        return MeResponse(
            user_id=str(user.id),
            name=user.name,
            srn=user.srn,
            email=user.email,
            role=user.role,
            team_id=user.team_id,
            mentor_team_ids=user.mentor_team_ids,
        )

    # ── Private Helpers ────────────────────────────────────────────────────────

    async def _upsert_user(self, pes_data: dict) -> User:
        """
        Upsert a user document from PES Auth response data.

        Creates the user on first login; updates name/email/role on subsequent logins.
        """
        srn = pes_data.get("srn", "").upper()
        existing = await User.find_one(User.srn == srn)

        if existing:
            # Update mutable fields that PES might change
            await existing.set({
                User.name: pes_data.get("name", existing.name),
                User.email: pes_data.get("email", existing.email),
                User.role: pes_data.get("role", existing.role),
                User.team_id: pes_data.get("team_id", existing.team_id),
                User.mentor_team_ids: pes_data.get("mentor_team_ids", existing.mentor_team_ids),
                User.updated_at: datetime.now(timezone.utc),
            })
            return existing

        # First login — create new user document
        user = User(
            srn=srn,
            name=pes_data.get("name", srn),
            email=pes_data.get("email", f"{srn.lower()}@pes.edu"),
            role=pes_data.get("role", "student"),
            team_id=pes_data.get("team_id"),
            mentor_team_ids=pes_data.get("mentor_team_ids", []),
        )
        await user.insert()
        logger.info("New user created from PES Auth: srn=%s role=%s", srn, user.role)
        return user

    async def _find_refresh_token(self, raw_token: str) -> RefreshToken:
        """
        Find a refresh token document by verifying the raw token against stored hashes.

        Searches only non-revoked tokens. Uses bcrypt verification.

        Raises:
            RefreshTokenInvalidError : No matching valid token found.
        """
        # Load all non-revoked, non-expired candidate tokens.
        # In production with many users, we'd add a secondary lookup field.
        # For this scale, bcrypt verification over recent tokens is acceptable.
        now = datetime.now(timezone.utc)
        candidates = await RefreshToken.find(
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > now,
        ).to_list()

        for candidate in candidates:
            if verify_refresh_token(raw_token, candidate.token_hash):
                return candidate

        raise RefreshTokenInvalidError()


# Module-level singleton
auth_service = AuthService()
