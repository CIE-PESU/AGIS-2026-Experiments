"""
auth/pes_client.py — Async HTTP client for PES Auth API validation.

Responsibilities:
  - POST student credentials (SRN + password) to PES Auth API
  - Return structured user data on success
  - Raise typed exceptions for timeout and auth failures
  - Never log the raw password

Errors raised:
  - PESAuthUnavailableError   → 503 (timeout or connection failure)
  - InvalidCredentialsError   → 401 (PES returned 401)
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.exceptions.base import InvalidCredentialsError, PESAuthUnavailableError

logger = logging.getLogger(__name__)


class PESAuthClient:
    """
    Thin async wrapper around the PES Authentication REST API.

    Usage:
        client = PESAuthClient()
        user_data = await client.validate_credentials(srn="PES2UG22CS001", password="...")
    """

    def __init__(self) -> None:
        self._timeout = httpx.Timeout(settings.PES_AUTH_TIMEOUT_SECONDS, connect=3.0)

    async def validate_credentials(self, srn: str, password: str) -> dict:
        """
        Validate student/staff credentials against PES Auth API.

        Args:
            srn: The Student Registration Number (e.g. PES2UG22CS001).
            password: The plaintext password — only sent over TLS to PES, never logged.

        Returns:
            A dict with at minimum: srn, name, email, role, team_id, mentor_team_ids.

        Raises:
            InvalidCredentialsError: PES returned 401 — wrong SRN or password.
            PESAuthUnavailableError: Network timeout or PES API is down.
        """
        payload = {"srn": srn, "password": password}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(settings.PES_AUTH_URL, json=payload)
        except httpx.TimeoutException as exc:
            logger.warning("PES Auth timeout for SRN=%s | %s", srn, exc)
            raise PESAuthUnavailableError(
                "PES Auth API did not respond within the timeout window."
            ) from exc
        except httpx.RequestError as exc:
            logger.error("PES Auth connection error for SRN=%s | %s", srn, exc)
            raise PESAuthUnavailableError(
                "Could not connect to PES Auth API. Please try again later."
            ) from exc

        if response.status_code == 401:
            logger.info("PES Auth rejected credentials for SRN=%s", srn)
            raise InvalidCredentialsError()

        if response.status_code != 200:
            logger.error(
                "PES Auth unexpected status %d for SRN=%s | body=%s",
                response.status_code,
                srn,
                response.text[:200],
            )
            raise PESAuthUnavailableError(
                f"PES Auth API returned an unexpected status: {response.status_code}"
            )

        try:
            data = response.json()
        except Exception as exc:
            logger.error("PES Auth returned non-JSON response for SRN=%s", srn)
            raise PESAuthUnavailableError("PES Auth API returned an invalid response.") from exc

        logger.info("PES Auth validated SRN=%s role=%s", srn, data.get("role"))
        return data


# Module-level singleton — avoids re-instantiating the client per request.
pes_auth_client = PESAuthClient()
