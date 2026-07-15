"""
auth/pes_client.py — Async HTTP client for PES Auth API validation.
"""

from __future__ import annotations

import logging

import httpx

from core.config import settings
from exceptions.base import InvalidCredentialsError, PESAuthUnavailableError

logger = logging.getLogger(__name__)


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