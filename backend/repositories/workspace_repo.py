"""
repositories/workspace_repo.py — Repository layer for workspaces collection.

All MongoDB reads and writes for Workspace entities go through this repository.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from models.workspace import Workspace, WorkspaceStatus, WorkspaceType
from repositories.base import BaseRepository

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkspaceRepository(BaseRepository[Workspace]):

    def __init__(self) -> None:
        super().__init__(Workspace)

    async def create(
        self,
        name: str,
        type: WorkspaceType = WorkspaceType.MENTOR,
        token_hash: Optional[str] = None,
        student_user_id: Optional[str] = None,
        mentor_id: Optional[str] = None,
        created_by_admin_id: Optional[str] = None,
    ) -> Workspace:
        """Create a new Workspace document."""
        workspace = Workspace(
            name=name,
            type=type,
            status=WorkspaceStatus.ACTIVE,
            token_hash=token_hash,
            student_user_id=student_user_id,
            mentor_id=mentor_id,
            created_by_admin_id=created_by_admin_id,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        await workspace.insert()
        return workspace

    async def find_active_workspaces(
        self,
        mentor_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> list[Workspace]:
        """Find active workspaces matching mentor_id or name."""
        if mentor_id:
            return await Workspace.find(
                Workspace.status == WorkspaceStatus.ACTIVE,
                Workspace.mentor_id == mentor_id,
            ).to_list()
        elif name:
            return await Workspace.find(
                Workspace.status == WorkspaceStatus.ACTIVE,
                Workspace.name == name,
            ).to_list()
        return []

    async def find_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """Lookup workspace by ObjectId string."""
        return await Workspace.get(workspace_id)

    async def find_by_token_hash(self, token_hash: str) -> Optional[Workspace]:
        """Lookup workspace by SHA-256 token hash."""
        return await Workspace.find_one(Workspace.token_hash == token_hash)

    async def find_by_student_user_id(self, student_user_id: str) -> Optional[Workspace]:
        """Lookup active student workspace by student user ID."""
        return await Workspace.find_one(
            Workspace.student_user_id == student_user_id,
            Workspace.type == WorkspaceType.STUDENT,
            Workspace.status == WorkspaceStatus.ACTIVE,
        )

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 50,
        type_filter: Optional[str] = None,
    ) -> tuple[list[Workspace], int]:
        """List all workspaces with pagination."""
        query = Workspace.find()
        if type_filter:
            query = Workspace.find(Workspace.type == type_filter)

        total = await query.count()
        items = await query.sort(-Workspace.created_at).skip(skip).limit(limit).to_list()
        return items, total

    async def revoke(self, workspace_id: str) -> Optional[Workspace]:
        """Mark workspace as revoked."""
        workspace = await Workspace.get(workspace_id)
        if workspace and workspace.status == WorkspaceStatus.ACTIVE:
            workspace.status = WorkspaceStatus.REVOKED
            workspace.revoked_at = utc_now()
            workspace.updated_at = utc_now()
            await workspace.save()
            logger.info("Workspace revoked: workspace_id=%s", workspace_id)
        return workspace

    async def delete(self, workspace_id: str) -> bool:
        """Hard-delete workspace document."""
        workspace = await Workspace.get(workspace_id)
        if workspace:
            await workspace.delete()
            return True
        return False


# Global singleton instance
workspace_repo = WorkspaceRepository()
