from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.data.france_bulk import build_france_query_plan
from app.models.bulk_job import BulkJob
from app.models.enums import SearchStatus
from app.repositories.bulk_job_repository import BulkJobRepository
from app.schemas.scraping import BulkScrapingStartRequest, BulkScrapingStartResponse, BulkScrapingStatusResponse
from app.services.bulk_job_persistence import bulk_job_to_state, schedule_sync_bulk_job
from app.workers.bulk_scraping_job import run_bulk_scraping_job
from app.workers.job_runner import BulkJobState, JobRunner, job_runner


class BulkScrapingService:
    def __init__(self, session: AsyncSession, runner: JobRunner | None = None) -> None:
        self.session = session
        self.runner = runner or job_runner
        self.settings = get_settings()
        self.bulk_job_repo = BulkJobRepository(session)

    async def start_bulk_scraping(self, payload: BulkScrapingStartRequest) -> BulkScrapingStartResponse:
        active = await self.bulk_job_repo.get_active()
        if active is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bulk job {active.job_id} is already active",
            )

        if self.runner.get_active_bulk_job() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A bulk job is already running in this process",
            )

        target_count = payload.target_count or self.settings.bulk_target_default
        max_queries = payload.max_queries or self.settings.bulk_max_queries
        queries = build_france_query_plan(
            cities=payload.cities,
            categories=payload.categories,
            max_queries=max_queries,
        )
        if not queries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No city/category combinations to scrape",
            )

        job_id = f"bulk-{uuid4().hex[:12]}"
        state = self.runner.start_bulk_job(
            self._build_job_wrapper(
                job_id=job_id,
                country=payload.country,
                target_count=target_count,
                cities=payload.cities,
                categories=payload.categories,
                max_queries=max_queries,
            ),
            country=payload.country,
            target_count=target_count,
            job_id=job_id,
        )
        self.runner.update_bulk_progress(state.job_id, total_queries=len(queries))

        await self.bulk_job_repo.create_job(
            job_id=state.job_id,
            country=payload.country,
            target_count=target_count,
            total_queries=len(queries),
            cities=payload.cities,
            categories=payload.categories,
            max_queries=max_queries,
        )
        await self.session.commit()
        schedule_sync_bulk_job(state)

        return BulkScrapingStartResponse(
            job_id=state.job_id,
            country=state.country,
            target_count=state.target_count,
            total_queries=len(queries),
            status=SearchStatus.RUNNING,
        )

    async def get_status(self, job_id: str) -> BulkScrapingStatusResponse:
        memory_job = self.runner.get_bulk_job(job_id)
        if memory_job is not None:
            return self._to_status_response(memory_job)

        db_job = await self.bulk_job_repo.get_by_job_id(job_id)
        if db_job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bulk job {job_id} not found",
            )
        return self._to_status_response(db_job)

    async def get_active_status(self) -> BulkScrapingStatusResponse | None:
        memory_job = self.runner.get_active_bulk_job()
        if memory_job is not None:
            return self._to_status_response(memory_job)

        db_job = await self.bulk_job_repo.get_active()
        if db_job is None:
            return None
        return self._to_status_response(db_job)

    async def pause_bulk_scraping(self, job_id: str) -> BulkScrapingStatusResponse:
        try:
            state = self.runner.request_bulk_pause(job_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        await self.bulk_job_repo.sync_control_flags(job_id, state)
        await self.session.commit()
        schedule_sync_bulk_job(state)
        return self._to_status_response(state)

    async def resume_bulk_scraping(self, job_id: str) -> BulkScrapingStatusResponse:
        db_job = await self.bulk_job_repo.get_by_job_id(job_id)
        if db_job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bulk job {job_id} not found",
            )

        memory_job = self.runner.get_bulk_job(job_id)
        if memory_job is None:
            memory_job = bulk_job_to_state(db_job)
            self.runner.register_bulk_job(memory_job)

        try:
            state = self.runner.request_bulk_resume(job_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        if state._task is None or state._task.done():
            self.runner.start_bulk_job_task(
                state,
                self._build_job_wrapper(
                    job_id=job_id,
                    country=db_job.country,
                    target_count=db_job.target_count,
                    cities=db_job.cities,
                    categories=db_job.categories,
                    max_queries=db_job.max_queries,
                ),
            )

        await self.bulk_job_repo.sync_control_flags(job_id, state)
        await self.session.commit()
        schedule_sync_bulk_job(state)
        return self._to_status_response(state)

    async def stop_bulk_scraping(self, job_id: str) -> BulkScrapingStatusResponse:
        try:
            state = self.runner.request_bulk_stop(job_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        await self.bulk_job_repo.upsert_from_state(state)
        await self.session.commit()
        schedule_sync_bulk_job(state)
        return self._to_status_response(state)

    def _build_job_wrapper(
        self,
        *,
        job_id: str,
        country: str,
        target_count: int,
        cities: list[str] | None,
        categories: list[str] | None,
        max_queries: int | None,
    ):
        async def job_wrapper() -> None:
            bulk_state = self.runner.get_bulk_job(job_id)
            if bulk_state is None:
                return
            await run_bulk_scraping_job(
                bulk_state.job_id,
                country=country,
                target_count=target_count,
                cities=cities,
                categories=categories,
                max_queries=max_queries,
                start_from_query_index=bulk_state.completed_queries,
            )

        return job_wrapper

    def _to_status_response(self, job: BulkJobState | BulkJob) -> BulkScrapingStatusResponse:
        return BulkScrapingStatusResponse(
            job_id=job.job_id,
            country=job.country,
            target_count=job.target_count,
            total_queries=job.total_queries,
            completed_queries=job.completed_queries,
            prospects_found=job.prospects_found,
            prospects_saved=job.prospects_saved,
            prospects_skipped_duplicates=job.prospects_skipped_duplicates,
            current_city=job.current_city,
            current_category=job.current_category,
            status=job.status,
            error=job.error,
        )
