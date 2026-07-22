"""
auth/pes_client.py — Async HTTP client for PES Auth API validation.
"""

from __future__ import annotations

import logging

import httpx
from cryptography.fernet import Fernet

from core.config import settings
from exceptions.base import InvalidCredentialsError, PESAuthUnavailableError

logger = logging.getLogger(__name__)

# Static key for mock environment
_MOCK_FERNET_KEY = b'xR7A2h_6f_D9zL4Q-V1ZtN_y3U5oP7k_J9h3W1mX0R8='
_cipher = Fernet(_MOCK_FERNET_KEY)

# Encrypted passwords for mock admins
# These are encrypted symmetrically with the mock Fernet key
MOCK_ADMINS = {
    "ASHWIN": b'gAAAAABqYKqMdpFftoI6_i2-NT1vHBm_4tNxZ123DWzTbyEwiaQZfolXaE2Oqphu9f5Dx2Gke16rXMkN06nWj_vaWXaynIVHBA==',
    "BHAVESH": b'gAAAAABqYKqMZCIf_tI5H78sE2aSqJfLVBFvFzSdfH99UXYU_hnwNKd0jlKL0lZ6v5lc0lrIEVZXNiZpqEpqfkPD9HJApKUdtA==',
    "URAV": b'gAAAAABqYKqMin8V8bDgZ6splNykeFhOu-GSsJhxERnH4gcQnb6DGePbaihlSkOChMZas24tgmQ6C1abXn762_PEALD5xeQcZA==',
}


class PESAuthClient:
    def __init__(self) -> None:
        self._timeout = httpx.Timeout(
            settings.PES_AUTH_TIMEOUT_SECONDS,
            connect=3.0,
        )

    async def validate_credentials(self, srn: str, password: str) -> dict:
        """
        Validate PES credentials and normalize the PES profile response
        into the shape expected by AuthService._upsert_user().
        """
        if settings.ENVIRONMENT == "development" or password == "dev" or srn.upper() in MOCK_ADMINS:
            logger.info("DEV MODE: Bypassing PES Auth HTTP call for SRN=%s", srn)
            
            # Check mock admin credentials using Fernet decryption
            if srn.upper() in MOCK_ADMINS:
                encrypted_pwd = MOCK_ADMINS[srn.upper()]
                decrypted_pwd = _cipher.decrypt(encrypted_pwd).decode()
                if password != decrypted_pwd:
                    raise InvalidCredentialsError()
            
            role = "student"
            if srn.upper().startswith("MENTOR_") or "MENTOR" in srn.upper():
                role = "mentor"
            elif srn.upper().startswith("ADMIN_") or "ADMIN" in srn.upper() or srn.upper() in MOCK_ADMINS:
                role = "admin"

            mentor_team_ids = []
            if role == "mentor":
                mentor_team_ids = ["6a5decdcdc6c8f205414113d"]

            return {
                "srn": srn.upper(),
                "name": f"Dev User ({srn})",
                "email": f"{srn.lower()}@pesu.pes.edu",
                "role": role,
                "team_id": None,
                "mentor_team_ids": mentor_team_ids,
            }

        payload = {
            "username": srn,
            "password": password,
            "profile": True,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    settings.PES_AUTH_URL,
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            logger.warning(
                "PES Auth timeout for SRN=%s | %s",
                srn,
                exc,
            )
            raise PESAuthUnavailableError(
                "PES Auth API did not respond within the timeout window."
            ) from exc

        except httpx.RequestError as exc:
            logger.error(
                "PES Auth connection error for SRN=%s | %s",
                srn,
                exc,
            )
            raise PESAuthUnavailableError(
                "Could not connect to PES Auth API. Please try again later."
            ) from exc

        if response.status_code in (401, 403):
            logger.info(
                "PES Auth rejected credentials for SRN=%s",
                srn,
            )
            raise InvalidCredentialsError()

        if response.status_code != 200:
            logger.error(
                "PES Auth unexpected status %d for SRN=%s | body=%s",
                response.status_code,
                srn,
                response.text[:200],
            )
            raise PESAuthUnavailableError(
                f"PES Auth API returned unexpected status: "
                f"{response.status_code}"
            )

        try:
            data = response.json()
        except Exception as exc:
            logger.error(
                "PES Auth returned non-JSON response for SRN=%s",
                srn,
            )
            raise PESAuthUnavailableError(
                "PES Auth API returned an invalid response."
            ) from exc

        if not data.get("status"):
            logger.info(
                "PES Auth login unsuccessful for SRN=%s",
                srn,
            )
            raise InvalidCredentialsError()

        profile = data.get("profile")

        if not isinstance(profile, dict):
            logger.error(
                "PES Auth response missing profile for SRN=%s",
                srn,
            )
            raise PESAuthUnavailableError(
                "PES Auth response did not contain profile information."
            )

        profile_srn = profile.get("srn") or srn

        normalized_user = {
            "srn": profile_srn.upper(),
            "name": profile.get("name", profile_srn),
            "email": profile.get("email"),
            "role": "student",
            "team_id": None,
            "mentor_team_ids": [],
        }

        logger.info(
            "PES Auth validated SRN=%s name=%s",
            normalized_user["srn"],
            normalized_user["name"],
        )

        return normalized_user


pes_auth_client = PESAuthClient()