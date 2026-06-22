from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.enums import WebsiteReason
from app.models.prospect import Prospect
from app.models.search import Search
from app.repositories.base import BaseRepository
from app.utils.url import normalize_maps_url


class ProspectRepository(BaseRepository[Prospect]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Prospect)

    def _apply_filters(
        self,
        stmt: Select[tuple[Prospect]],
        *,
        city: str | None = None,
        category: str | None = None,
        has_website: bool | None = None,
        website_reason: WebsiteReason | None = None,
    ) -> Select[tuple[Prospect]]:
        city = city.strip() if city else None
        category = category.strip() if category else None
        if city:
            stmt = stmt.join(Search).where(Search.city.ilike(f"%{city}%"))
        if category:
            stmt = stmt.where(Prospect.category.ilike(f"%{category}%"))
        if has_website is not None:
            stmt = stmt.where(Prospect.has_website == has_website)
        if website_reason is not None:
            stmt = stmt.where(Prospect.website_reason == website_reason)
        return stmt

    async def list_filtered(
        self,
        *,
        city: str | None = None,
        category: str | None = None,
        has_website: bool | None = None,
        website_reason: WebsiteReason | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Prospect]:
        stmt = (
            select(Prospect)
            .options(joinedload(Prospect.search))
            .order_by(Prospect.created_at.desc())
        )
        stmt = self._apply_filters(
            stmt,
            city=city,
            category=category,
            has_website=has_website,
            website_reason=website_reason,
        )
        result = await self.session.execute(stmt.offset(skip).limit(limit))
        return list(result.scalars().unique().all())

    async def count_filtered(
        self,
        *,
        city: str | None = None,
        category: str | None = None,
        has_website: bool | None = None,
        website_reason: WebsiteReason | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Prospect)
        stmt = self._apply_filters(
            stmt,
            city=city,
            category=category,
            has_website=has_website,
            website_reason=website_reason,
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_with_search(self, prospect_id: int) -> Prospect | None:
        result = await self.session.execute(
            select(Prospect)
            .options(joinedload(Prospect.search))
            .where(Prospect.id == prospect_id)
        )
        return result.scalars().unique().first()

    async def get_stats(self) -> dict[str, int]:
        total_result = await self.session.execute(select(func.count()).select_from(Prospect))
        with_result = await self.session.execute(
            select(func.count()).select_from(Prospect).where(Prospect.has_website.is_(True))
        )
        total = int(total_result.scalar_one())
        with_website = int(with_result.scalar_one())
        return {
            "total": total,
            "with_website": with_website,
            "without_website": total - with_website,
        }

    async def exists_globally(
        self,
        *,
        maps_url: str | None,
        business_name: str,
        address: str | None,
    ) -> bool:
        normalized_url = normalize_maps_url(maps_url)
        if normalized_url:
            url_result = await self.session.execute(
                select(func.count())
                .select_from(Prospect)
                .where(Prospect.maps_url == normalized_url)
            )
            if int(url_result.scalar_one()) > 0:
                return True

        name_address_result = await self.session.execute(
            select(func.count())
            .select_from(Prospect)
            .where(
                Prospect.business_name == business_name,
                Prospect.address == address,
            )
        )
        return int(name_address_result.scalar_one()) > 0

    async def exists_for_search(
        self,
        search_id: int,
        business_name: str,
        address: str | None,
        maps_url: str | None = None,
    ) -> bool:
        normalized_url = normalize_maps_url(maps_url)
        if normalized_url:
            url_result = await self.session.execute(
                select(func.count())
                .select_from(Prospect)
                .where(
                    Prospect.search_id == search_id,
                    Prospect.maps_url == normalized_url,
                )
            )
            if int(url_result.scalar_one()) > 0:
                return True

        stmt = select(func.count()).select_from(Prospect).where(
            Prospect.search_id == search_id,
            Prospect.business_name == business_name,
            Prospect.address == address,
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one()) > 0
