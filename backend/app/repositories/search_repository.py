from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SearchStatus
from app.models.search import Search
from app.repositories.base import BaseRepository


class SearchRepository(BaseRepository[Search]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Search)

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Search]:
        result = await self.session.execute(
            select(Search).order_by(Search.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(self, search_id: int, status: SearchStatus) -> Search | None:
        search = await self.get_by_id(search_id)
        if search is None:
            return None
        search.status = status
        await self.session.flush()
        await self.session.refresh(search)
        return search

    async def mark_running_as_failed(self) -> int:
        result = await self.session.execute(
            update(Search)
            .where(Search.status == SearchStatus.RUNNING)
            .values(status=SearchStatus.FAILED)
        )
        await self.session.flush()
        return int(result.rowcount or 0)
