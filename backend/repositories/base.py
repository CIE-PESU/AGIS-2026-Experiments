"""
Generic async CRUD base repository.
All repository classes extend this. Only Beanie Document subclasses are valid as T.
"""

from typing import Generic, TypeVar, Optional, Type
from beanie import Document

T = TypeVar("T", bound=Document)


class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T]) -> None:
        self.model = model

    async def find_by_id(self, doc_id: str) -> Optional[T]:
        return await self.model.get(doc_id)

    async def save(self, document: T) -> T:
        await document.save()
        return document

    async def delete(self, document: T) -> None:
        await document.delete()
