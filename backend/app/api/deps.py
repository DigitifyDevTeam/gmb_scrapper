from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.services.bulk_scraping_service import BulkScrapingService
from app.services.prospect_service import ProspectService
from app.services.scraping_service import ScrapingService
from app.services.search_service import SearchService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_search_service(session: AsyncSession = Depends(get_session)) -> SearchService:
    return SearchService(session)


def get_scraping_service(session: AsyncSession = Depends(get_session)) -> ScrapingService:
    return ScrapingService(session)


def get_bulk_scraping_service(session: AsyncSession = Depends(get_session)) -> BulkScrapingService:
    return BulkScrapingService(session)


def get_prospect_service(session: AsyncSession = Depends(get_session)) -> ProspectService:
    return ProspectService(session)
