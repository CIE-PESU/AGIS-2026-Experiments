"""
repositories/workspace_repo.py — Repository layer for workspaces collection.

All MongoDB reads and writes for Workspace entities go through this repository.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from models.workspace import Workspace, WorkspaceStatus, WorkspaceType
from repositories.base import BaseRepository

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


class WorkspaceRepository(BaseRepository[Workspace]):

    def __init__(self) -> None:
        super().__init__(Workspace)

    async def create(
        self,
        name: str,
        type: WorkspaceType = WorkspaceType.MENTOR,
        token_hash: str | None = None,
        student_user_id: str | None = None,
        mentor_id: str | None = None,
        created_by_admin_id: str | None = None,
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
        mentor_id: str | None = None,
        name: str | None = None,
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

    async def find_by_id(self, workspace_id: str) -> Workspace | None:
        """Lookup workspace by ObjectId string."""
        return await Workspace.get(workspace_id)

    async def find_by_token_hash(self, token_hash: str) -> Workspace | None:
        """Lookup workspace by SHA-256 token hash."""
        return await Workspace.find_one(Workspace.token_hash == token_hash)

    async def find_by_student_user_id(self, student_user_id: str) -> Workspace | None:
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
        type_filter: str | None = None,
    ) -> tuple[list[Workspace], int]:
        """List all workspaces with pagination."""
        query = Workspace.find()
        if type_filter:
            query = Workspace.find(Workspace.type == type_filter)

        total = await query.count()
        items = await query.sort(-Workspace.created_at).skip(skip).limit(limit).to_list()
        return items, total

    async def revoke(self, workspace_id: str) -> Workspace | None:
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
