"""
api/v1/workspace.py — Public Workspace magic link redemption endpoint.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Request, status

from schemas.workspace import WorkspaceAccessRequest
from services.workspace_service import workspace_service
from utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace", tags=["Workspace"])


@router.post(
    "/access",
    status_code=status.HTTP_200_OK,
    summary="Redeem workspace magic link token",
    description=(
        "Exchanges a valid, active magic link token for a signed 7-day access JWT. "
        "Allows subsequent frontend navigation without token parameters in the address bar."
    ),
)
async def redeem_magic_link(request: Request, body: WorkspaceAccessRequest):
    """
    POST /workspace/access

    Errors:
        401 TOKEN_INVALID — missing, invalid, or revoked token.
    """
    result = await workspace_service.redeem_magic_link(raw_token=body.token)
    return success_response(data=result.model_dump(), request=request)
