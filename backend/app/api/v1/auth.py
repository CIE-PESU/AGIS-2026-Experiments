"""
api/v1/auth.py — Auth API route handlers.

Endpoints:
  POST /auth/login    → login
  POST /auth/refresh  → refresh_tokens
  POST /auth/logout   → logout
  GET  /auth/me       → get current user profile

All responses wrapped in the standard envelope:
  { "data": {...}, "meta": { "request_id": "...", "timestamp": "..." } }

Route handlers are thin — they only validate input, call the service, and
format the response. No business logic here.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.dependencies.auth import get_current_user
from app.schemas.auth import (
    CurrentUser,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
)
from app.services.auth_service import auth_service
from app.utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Login with SRN and password",
    description=(
        "Authenticates the user via PES Auth API. "
        "Returns a short-lived JWT access token and a long-lived refresh token. "
        "Rate limited to 5 requests per minute per IP."
    ),
)
async def login(request: Request, body: LoginRequest):
    """
    POST /auth/login

    Validates SRN + password against PES Auth API. Returns access_token,
    refresh_token, role, and basic user info.

    Errors:
      401 INVALID_CREDENTIALS   — wrong SRN or password
      422 VALIDATION_ERROR      — SRN format invalid
      503 PES_AUTH_UNAVAILABLE  — PES timed out
      429 RATE_LIMIT_EXCEEDED   — too many attempts
    """
    result = await auth_service.login(srn=body.srn, password=body.password)
    return success_response(data=result.model_dump(), request=request)


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description=(
        "Exchanges a valid refresh token for a new access token and a new refresh token. "
        "Old refresh token is invalidated immediately (token rotation)."
    ),
)
async def refresh_tokens(request: Request, body: RefreshRequest):
    """
    POST /auth/refresh

    Rotates refresh token. Client must update both stored tokens.

    Errors:
      401 REFRESH_TOKEN_INVALID — token not found or tampered
      401 REFRESH_TOKEN_EXPIRED — past 7-day TTL
    """
    result = await auth_service.refresh_tokens(raw_refresh_token=body.refresh_token)
    return success_response(data=result.model_dump(), request=request)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout and revoke refresh token",
    description=(
        "Revokes the provided refresh token server-side. "
        "The access token expires naturally at its exp. "
        "Client should discard both tokens immediately."
    ),
)
async def logout(
    request: Request,
    body: LogoutRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """
    POST /auth/logout (requires valid JWT)

    Revokes refresh token. Idempotent — calling with an already-revoked token
    does not raise an error.
    """
    await auth_service.logout(raw_refresh_token=body.refresh_token)
    # 204 No Content — FastAPI returns empty body automatically
    return None


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Returns the profile of the currently authenticated user based on the JWT.",
)
async def get_me(
    request: Request,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """
    GET /auth/me (requires valid JWT)

    Returns full user profile from MongoDB (not just JWT claims).

    Errors:
      401           — missing, expired, or invalid token
    """
    profile = await auth_service.get_current_user_profile(user_id=current_user.user_id)
    return success_response(data=profile.model_dump(), request=request)
