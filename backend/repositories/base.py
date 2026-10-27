"""
Generic async CRUD base repository.
All repository classes extend this. Only Beanie Document subclasses are valid as T.
"""

from typing import Generic, TypeVar

from beanie import Document

T = TypeVar("T", bound=Document)


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T]) -> None:
        self.model = model

    async def find_by_id(self, doc_id: str) -> T | None:
        return await self.model.get(doc_id)

    async def save(self, document: T) -> T:
        await document.save()
        return document

    async def delete(self, document: T) -> None:
        await document.delete()
