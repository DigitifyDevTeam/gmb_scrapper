from fastapi import APIRouter, Depends, Query

from app.api.deps import get_search_service
from app.schemas.search import SearchCreate, SearchListResponse, SearchRead
from app.services.search_service import SearchService

router = APIRouter(prefix="/searches", tags=["searches"])


@router.post("", response_model=SearchRead, status_code=201)
async def create_search(
    payload: SearchCreate,
    service: SearchService = Depends(get_search_service),
) -> SearchRead:
    search = await service.create_search(payload)
    return SearchRead.model_validate(search)


@router.get("", response_model=SearchListResponse)
async def list_searches(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: SearchService = Depends(get_search_service),
) -> SearchListResponse:
    items, total = await service.list_searches(skip=skip, limit=limit)
    return SearchListResponse(
        items=[SearchRead.model_validate(item) for item in items],
        total=total,
    )


@router.get("/{search_id}", response_model=SearchRead)
async def get_search(
    search_id: int,
    service: SearchService = Depends(get_search_service),
) -> SearchRead:
    search = await service.get_search(search_id)
    return SearchRead.model_validate(search)
