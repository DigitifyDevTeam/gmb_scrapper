from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search import Search
from app.repositories.search_repository import SearchRepository
from app.schemas.search import SearchCreate


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = SearchRepository(session)

    async def create_search(self, payload: SearchCreate) -> Search:
        search = Search(
            country=payload.country.strip(),
            city=payload.city.strip(),
            category=payload.category.strip(),
        )
        return await self.repository.create(search)

    async def list_searches(self, skip: int = 0, limit: int = 100) -> tuple[list[Search], int]:
        items = await self.repository.list_all(skip=skip, limit=limit)
        total = await self.repository.count()
        return items, total

    async def get_search(self, search_id: int) -> Search:
        search = await self.repository.get_by_id(search_id)
        if search is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Search {search_id} not found",
            )
        return search
