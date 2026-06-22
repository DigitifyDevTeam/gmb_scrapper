from fastapi import APIRouter, Depends, Query

from app.api.deps import get_prospect_service
from app.models.enums import WebsiteReason
from app.schemas.common import PaginatedResponse
from app.schemas.prospect import ProspectFilters, ProspectRead, ProspectStats
from app.services.prospect_service import ProspectService

router = APIRouter(prefix="/prospects", tags=["prospects"])


@router.get("/stats", response_model=ProspectStats)
async def get_prospect_stats(
    service: ProspectService = Depends(get_prospect_service),
) -> ProspectStats:
    return await service.get_stats()


@router.get("", response_model=PaginatedResponse[ProspectRead])
async def list_prospects(
    city: str | None = Query(default=None),
    category: str | None = Query(default=None),
    has_website: bool | None = Query(default=None),
    website_reason: WebsiteReason | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: ProspectService = Depends(get_prospect_service),
) -> PaginatedResponse[ProspectRead]:
    filters = ProspectFilters(
        city=city,
        category=category,
        has_website=has_website,
        website_reason=website_reason,
        page=page,
        page_size=page_size,
    )
    return await service.list_prospects(filters)


@router.get("/{prospect_id}", response_model=ProspectRead)
async def get_prospect(
    prospect_id: int,
    service: ProspectService = Depends(get_prospect_service),
) -> ProspectRead:
    return await service.get_prospect(prospect_id)
