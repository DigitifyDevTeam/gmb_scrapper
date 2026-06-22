from fastapi import APIRouter, Depends

from app.api.deps import get_bulk_scraping_service, get_scraping_service
from app.schemas.scraping import (
    BulkScrapingStartRequest,
    BulkScrapingStartResponse,
    BulkScrapingStatusResponse,
    ScrapingStartRequest,
    ScrapingStartResponse,
    ScrapingStatusResponse,
)
from app.services.bulk_scraping_service import BulkScrapingService
from app.services.scraping_service import ScrapingService

router = APIRouter(prefix="/scraping", tags=["scraping"])


@router.post("/start", response_model=ScrapingStartResponse)
async def start_scraping(
    payload: ScrapingStartRequest,
    service: ScrapingService = Depends(get_scraping_service),
) -> ScrapingStartResponse:
    return await service.start_scraping(payload.search_id)


@router.post("/bulk/start", response_model=BulkScrapingStartResponse)
async def start_bulk_scraping(
    payload: BulkScrapingStartRequest,
    service: BulkScrapingService = Depends(get_bulk_scraping_service),
) -> BulkScrapingStartResponse:
    return await service.start_bulk_scraping(payload)


@router.get("/status/{job_id}", response_model=ScrapingStatusResponse)
async def get_scraping_status(
    job_id: str,
    service: ScrapingService = Depends(get_scraping_service),
) -> ScrapingStatusResponse:
    return service.get_status(job_id)


@router.get("/bulk/active", response_model=BulkScrapingStatusResponse | None)
async def get_active_bulk_scraping(
    service: BulkScrapingService = Depends(get_bulk_scraping_service),
) -> BulkScrapingStatusResponse | None:
    return await service.get_active_status()


@router.get("/bulk/status/{job_id}", response_model=BulkScrapingStatusResponse)
async def get_bulk_scraping_status(
    job_id: str,
    service: BulkScrapingService = Depends(get_bulk_scraping_service),
) -> BulkScrapingStatusResponse:
    return await service.get_status(job_id)


@router.post("/bulk/pause/{job_id}", response_model=BulkScrapingStatusResponse)
async def pause_bulk_scraping(
    job_id: str,
    service: BulkScrapingService = Depends(get_bulk_scraping_service),
) -> BulkScrapingStatusResponse:
    return await service.pause_bulk_scraping(job_id)


@router.post("/bulk/resume/{job_id}", response_model=BulkScrapingStatusResponse)
async def resume_bulk_scraping(
    job_id: str,
    service: BulkScrapingService = Depends(get_bulk_scraping_service),
) -> BulkScrapingStatusResponse:
    return await service.resume_bulk_scraping(job_id)


@router.post("/bulk/stop/{job_id}", response_model=BulkScrapingStatusResponse)
async def stop_bulk_scraping(
    job_id: str,
    service: BulkScrapingService = Depends(get_bulk_scraping_service),
) -> BulkScrapingStatusResponse:
    return await service.stop_bulk_scraping(job_id)
