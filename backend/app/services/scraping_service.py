from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SearchStatus
from app.repositories.search_repository import SearchRepository
from app.schemas.scraping import ScrapingStartResponse, ScrapingStatusResponse
from app.workers.job_runner import JobRunner, job_runner
from app.workers.scraping_job import run_scraping_job


class ScrapingService:
    def __init__(self, session: AsyncSession, runner: JobRunner | None = None) -> None:
        self.search_repository = SearchRepository(session)
        self.runner = runner or job_runner

    async def start_scraping(self, search_id: int) -> ScrapingStartResponse:
        search = await self.search_repository.get_by_id(search_id)
        if search is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Search {search_id} not found",
            )

        if search.status == SearchStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Search {search_id} is already running",
            )

        job_id = f"search-{search_id}"
        await self.search_repository.update_status(search_id, SearchStatus.RUNNING)

        async def job_wrapper() -> None:
            await run_scraping_job(search_id)

        self.runner.start_job(job_id, search_id, job_wrapper)

        return ScrapingStartResponse(
            job_id=job_id,
            search_id=search_id,
            status=SearchStatus.RUNNING,
        )

    def get_status(self, job_id: str) -> ScrapingStatusResponse:
        job = self.runner.get_job(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        return ScrapingStatusResponse(
            job_id=job.job_id,
            search_id=job.search_id,
            status=job.status,
            prospects_found=job.prospects_found,
            prospects_saved=job.prospects_saved,
            error=job.error,
        )
