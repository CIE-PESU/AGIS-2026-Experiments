"""
services/workspace_service.py — Business logic for Workspace creation, magic link redemption, and revocation.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import BackgroundTasks

from auth.jwt import create_access_token, create_refresh_token
from core.config import settings
from core.constants import UserRole
from exceptions.base import (
    RefreshTokenInvalidError,
    SessionNotFoundError,
    TokenInvalidError,
    ValidationException,
)
from models.refresh_token import RefreshToken
from models.workspace import Workspace, WorkspaceStatus, WorkspaceType
from repositories.session_repo import session_repo
from repositories.workspace_repo import workspace_repo
from schemas.workspace import WorkspaceAccessResponse, WorkspaceResponse

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(raw_token: str) -> str:
    """Compute deterministic SHA-256 hash of a magic token string."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


class WorkspaceService:
    """Handles Workspace lifecycle, magic link access token exchange, and cascading data revocation."""

    async def create_magic_link_workspace(
        self,
        name: str,
        admin_id: str,
        mentor_id: Optional[str] = None,
        base_url: str = "https://agis.ai",
    ) -> tuple[str, WorkspaceResponse]:
        """
        Admin action: Generate a new 1:1 Isolated Mentor Workspace with a high-entropy magic link token.

        Automatically revokes pre-existing active workspaces for this mentor to enforce 1 active workspace constraint.

        Returns:
            Tuple of (raw_token, WorkspaceResponse).
        """
        if not name or not name.strip():
            raise ValidationException(message="Workspace name cannot be empty.", field="name")

        clean_name = name.strip()

        # Enforce 1 Active Workspace per mentor: Auto-revoke any pre-existing active workspaces for mentor_id or name
        existing_active = await workspace_repo.find_active_workspaces(mentor_id=mentor_id, name=clean_name)
        for old_ws in existing_active:
            await workspace_repo.revoke(old_ws.workspace_id)
            logger.info("Auto-revoked prior active workspace for mentor re-issuance: workspace_id=%s", old_ws.workspace_id)

        raw_token = secrets.token_urlsafe(32)
        token_digest = hash_token(raw_token)

        workspace = await workspace_repo.create(
            name=clean_name,
            type=WorkspaceType.MENTOR,
            token_hash=token_digest,
            created_by_admin_id=admin_id,
            mentor_id=mentor_id,
        )

        magic_url = f"{base_url.rstrip('/')}/workspace/{raw_token}"

        response = WorkspaceResponse(
            workspace_id=workspace.workspace_id,
            name=workspace.name,
            type=workspace.type.value,
            status=workspace.status.value,
            mentor_id=workspace.mentor_id,
            magic_url=magic_url,
            created_at=workspace.created_at.isoformat(),
        )

        logger.info("Created magic link workspace: workspace_id=%s admin_id=%s mentor_id=%s", workspace.workspace_id, admin_id, mentor_id)
        return raw_token, response

    async def redeem_magic_link(self, raw_token: str) -> WorkspaceAccessResponse:
        """
        Public action: Redeem magic link token for access + refresh JWTs.

        Validates token SHA-256 digest against DB. Checks if active.
        Issues access JWT with role="mentor_workspace" and workspace_id.
        Issues refresh token with workspace_id explicitly populated.
        """
        if not raw_token or not raw_token.strip():
            raise TokenInvalidError("Magic token is missing.")

        token_digest = hash_token(raw_token)
        workspace = await workspace_repo.find_by_token_hash(token_digest)

        if not workspace or not workspace.is_active:
            raise TokenInvalidError("Invalid or revoked workspace magic link.")

        # Synthetic user ID representing this workspace's primary subject claim
        synthetic_sub = f"ws_{workspace.workspace_id}"

        # Create access JWT carrying role="mentor_workspace" and workspace_id (7-day validity, no refresh token)
        access_token = create_access_token(
            user_id=synthetic_sub,
            role=UserRole.MENTOR_WORKSPACE,
            name=workspace.name,
            workspace_id=workspace.workspace_id,
        )

        logger.info("Magic link redeemed successfully: workspace_id=%s", workspace.workspace_id)

        return WorkspaceAccessResponse(
            access_token=access_token,
            expires_in=settings.JWT_EXPIRY_MINUTES * 60,
            role=UserRole.MENTOR_WORKSPACE,
            workspace_id=workspace.workspace_id,
            name=workspace.name,
        )

    async def list_workspaces(
        self,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[WorkspaceResponse], int]:
        """Admin action: List all created workspaces."""
        skip = (page - 1) * limit
        items, total = await workspace_repo.list_all(skip=skip, limit=limit)
        responses = [
            WorkspaceResponse(
                workspace_id=item.workspace_id,
                name=item.name,
                type=item.type.value,
                status=item.status.value,
                created_at=item.created_at.isoformat(),
                revoked_at=item.revoked_at.isoformat() if item.revoked_at else None,
            )
            for item in items
        ]
        return responses, total

    async def revoke_workspace(
        self,
        workspace_id: str,
        background_tasks: BackgroundTasks,
    ) -> WorkspaceResponse:
        """
        Admin action: Revoke a workspace immediately and schedule async data cleanup.

        - Instantly sets Workspace.status = "revoked"
        - Instantly revokes all RefreshTokens for workspace_id
        - Dispatches async task to delete Sessions, comments, and application data (retaining AuditLogs)
        """
        workspace = await workspace_repo.find_by_id(workspace_id)
        if not workspace:
            raise SessionNotFoundError("Workspace not found.")

        # 1. Immediately revoke workspace status
        workspace = await workspace_repo.revoke(workspace_id)

        # 2. Immediately revoke all RefreshTokens for workspace_id
        await RefreshToken.find(RefreshToken.workspace_id == workspace_id).update(
            {"$set": {"revoked": True}}
        )

        # 3. Audit log revocation
        from services.audit_service import audit_service
        await audit_service.log_event(
            session_id=None,
            event="WORKSPACE_REVOKED",
            actor="admin",
            actor_role="admin",
            metadata={"workspace_id": workspace_id, "name": workspace.name},
        )

        # 4. Schedule background data cleanup
        background_tasks.add_task(self._async_purge_workspace_data, workspace_id)

        logger.info("Workspace revoked and cleanup scheduled: workspace_id=%s", workspace_id)

        return WorkspaceResponse(
            workspace_id=workspace.workspace_id,
            name=workspace.name,
            type=workspace.type.value,
            status=workspace.status.value,
            created_at=workspace.created_at.isoformat(),
            revoked_at=workspace.revoked_at.isoformat() if workspace.revoked_at else None,
        )

    @staticmethod
    async def _async_purge_workspace_data(workspace_id: str) -> None:
        """
        Background task: Cascading deletion of sessions, comments, and tokens for a revoked workspace.

        AuditLog entries ARE PRESERVED for compliance and operational audit trails.
        """
        try:
            logger.info("Starting background data purge for workspace_id=%s", workspace_id)

            # Delete comments on sessions belonging to this workspace
            sessions = await session_repo.find_by_workspace_id(workspace_id)
            session_ids = [str(s.id) for s in sessions]

            if session_ids:
                from models.comment import MentorComment
                await MentorComment.find({"session_id": {"$in": session_ids}}).delete()

            # Delete refresh tokens
            await RefreshToken.find(RefreshToken.workspace_id == workspace_id).delete()

            # Delete session documents
            deleted_sessions_count = await session_repo.delete_by_workspace_id(workspace_id)

            logger.info(
                "Background data purge completed for workspace_id=%s (deleted %d sessions)",
                workspace_id,
                deleted_sessions_count,
            )
        except Exception as exc:
            logger.exception("Error during background workspace data purge: workspace_id=%s | %s", workspace_id, str(exc))


# Global singleton
workspace_service = WorkspaceService()
