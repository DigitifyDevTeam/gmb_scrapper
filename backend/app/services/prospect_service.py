import math

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.prospect_repository import ProspectRepository
from app.schemas.common import PaginatedResponse
from app.schemas.prospect import ProspectFilters, ProspectRead, ProspectStats, TestimonialRead


class ProspectService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = ProspectRepository(session)

    async def list_prospects(
        self,
        filters: ProspectFilters,
    ) -> PaginatedResponse[ProspectRead]:
        skip = (filters.page - 1) * filters.page_size
        items = await self.repository.list_filtered(
            city=filters.city,
            category=filters.category,
            has_website=filters.has_website,
            website_reason=filters.website_reason,
            skip=skip,
            limit=filters.page_size,
        )
        total = await self.repository.count_filtered(
            city=filters.city,
            category=filters.category,
            has_website=filters.has_website,
            website_reason=filters.website_reason,
        )

        prospect_reads = [self._to_read(item) for item in items]
        total_pages = max(1, math.ceil(total / filters.page_size)) if total else 0

        return PaginatedResponse(
            items=prospect_reads,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=total_pages,
        )

    async def get_prospect(self, prospect_id: int) -> ProspectRead:
        prospect = await self.repository.get_with_search(prospect_id)
        if prospect is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prospect {prospect_id} not found",
            )
        return self._to_read(prospect)

    async def get_stats(self) -> ProspectStats:
        stats = await self.repository.get_stats()
        return ProspectStats(**stats)

    def _to_read(self, prospect) -> ProspectRead:
        testimonials = [
            TestimonialRead(**item)
            for item in (prospect.testimonials or [])
            if isinstance(item, dict) and item.get("text")
        ]
        return ProspectRead(
            id=prospect.id,
            search_id=prospect.search_id,
            business_name=prospect.business_name,
            category=prospect.category,
            address=prospect.address,
            phone=prospect.phone,
            website=prospect.website,
            rating=prospect.rating,
            review_count=prospect.review_count,
            maps_url=prospect.maps_url,
            has_website=prospect.has_website,
            website_reason=prospect.website_reason,
            testimonials=testimonials,
            created_at=prospect.created_at,
            city=prospect.search.city if prospect.search else None,
            country=prospect.search.country if prospect.search else None,
        )
