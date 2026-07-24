"""
repositories/comment_repo.py — CRUD for the `mentor_comments` collection.

Rules enforced at this layer:
  - find_by_session ALWAYS excludes soft-deleted comments (deleted=True).
  - find_by_id_and_mentor returns None if the comment exists but belongs to a
    different mentor — prevents information leakage (same pattern as session repo).
  - soft_delete sets deleted=True; never physically removes a document.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from beanie import PydanticObjectId

from models.comment import MentorComment
from repositories.base import BaseRepository
from services.comment_service import Comment  # dataclass with comment_id


class CommentRepository(BaseRepository[MentorComment]):
    def __init__(self) -> None:
        super().__init__(MentorComment)

    async def create(
        self,
        session_id: str,
        mentor_id: str,
        mentor_name: str,
        comment: str,
    ) -> MentorComment:
        """
        Persist a new mentor comment.

        Returns:
            The newly created MentorComment document with its generated _id.
        """
        doc = MentorComment(
            session_id=session_id,
            mentor_id=mentor_id,
            mentor_name=mentor_name,
            comment=comment,
        )
        await doc.insert()
        return Comment(
            comment_id=str(doc.id),
            session_id=doc.session_id,
            mentor_id=doc.mentor_id,
            mentor_name=doc.mentor_name,
            comment=doc.comment,
            created_at=doc.created_at,
            deleted=doc.deleted,
        )

    async def find_by_session(self, session_id: str) -> list[MentorComment]:
        """
        Return all non-deleted comments for a session, ordered chronologically.

        Soft-deleted comments (deleted=True) are ALWAYS excluded.
        """
        docs = (
            await MentorComment.find(
                MentorComment.session_id == session_id,
                MentorComment.deleted == False,  # noqa: E712
            )
            .sort(+MentorComment.created_at)  # type: ignore[arg-type]
            .to_list()
        )
        return [
            Comment(
                comment_id=str(d.id),
                session_id=d.session_id,
                mentor_id=d.mentor_id,
                mentor_name=d.mentor_name,
                comment=d.comment,
                created_at=d.created_at.isoformat(),
                deleted=d.deleted,
            )
            for d in docs
        ]

    async def find_by_id(self, comment_id: str) -> Optional[MentorComment]:
        """
        Fetch a comment by its _id. No ownership filter.
        Returns None if not found.
        """
        try:
            oid = PydanticObjectId(comment_id)
        except Exception:
            return None
        return await MentorComment.get(oid)

    async def find_by_id_and_mentor(
        self, comment_id: str, mentor_id: str
    ) -> Optional[MentorComment]:
        """
        Ownership-filtered fetch.
        Returns None if the comment exists but belongs to a different mentor.
        This intentionally returns None (not 403) to prevent information leakage.
        """
        try:
            oid = PydanticObjectId(comment_id)
        except Exception:
            return None
        return await MentorComment.find_one(
            MentorComment.id == oid,  # type: ignore[arg-type]
            MentorComment.mentor_id == mentor_id,
            MentorComment.deleted == False,  # noqa: E712
        )

    async def soft_delete(self, comment_id: str) -> bool:
        """
        Soft-delete a comment by setting deleted=True.

        Returns:
            True  — comment was found and marked deleted.
            False — comment not found (already deleted or bad ID).
        """
        try:
            oid = PydanticObjectId(comment_id)
        except Exception:
            return False

        comment = await MentorComment.get(oid)
        if comment is None or comment.deleted:
            return False

        comment.deleted = True
        await comment.save()
        return True


comment_repo = CommentRepository()
