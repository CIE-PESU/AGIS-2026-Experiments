"""
dependencies/pagination.py — Reusable FastAPI pagination dependency.

Usage in a route:
    from dependencies.pagination import PaginationParams

    @router.get("/items")
    async def list_items(pagination: PaginationParams = Depends()):
        items = await repo.find(page=pagination.page, limit=pagination.limit)
        return paginated_response(data=items, ..., page=pagination.page, limit=pagination.limit, total=total)
"""

from __future__ import annotations

from fastapi import Query


class PaginationParams:
    """
    Standard pagination query parameters.
    Inject via Depends() on any paginated list endpoint.
    """

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number (1-indexed)."),
        limit: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)."),
    ) -> None:
        self.page = page
        self.limit = limit
        self.skip = (page - 1) * limit
