from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bulk_job import BulkJob
from app.models.enums import SearchStatus
from app.repositories.base import BaseRepository
from app.workers.job_runner import BulkJobState


class BulkJobRepository(BaseRepository[BulkJob]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BulkJob)

    async def get_by_job_id(self, job_id: str) -> BulkJob | None:
        return await self.session.get(BulkJob, job_id)

    async def list_by_status(self, statuses: list[SearchStatus]) -> list[BulkJob]:
        result = await self.session.execute(
            select(BulkJob).where(BulkJob.status.in_(statuses)).order_by(BulkJob.started_at.desc())
        )
        return list(result.scalars().all())

    async def get_active(self) -> BulkJob | None:
        jobs = await self.list_by_status([SearchStatus.RUNNING, SearchStatus.PAUSED])
        return jobs[0] if jobs else None

    async def upsert_from_state(self, state: BulkJobState) -> BulkJob:
        existing = await self.get_by_job_id(state.job_id)
        if existing is None:
            entity = BulkJob(
                job_id=state.job_id,
                country=state.country,
                target_count=state.target_count,
                total_queries=state.total_queries,
                completed_queries=state.completed_queries,
                prospects_found=state.prospects_found,
                prospects_saved=state.prospects_saved,
                prospects_skipped_duplicates=state.prospects_skipped_duplicates,
                current_city=state.current_city,
                current_category=state.current_category,
                status=state.status,
                pause_requested=state.pause_requested,
                stop_requested=state.stop_requested,
                error=state.error,
                started_at=state.started_at,
                finished_at=state.finished_at,
            )
            return await self.create(entity)

        existing.total_queries = state.total_queries
        existing.completed_queries = state.completed_queries
        existing.prospects_found = state.prospects_found
        existing.prospects_saved = state.prospects_saved
        existing.prospects_skipped_duplicates = state.prospects_skipped_duplicates
        existing.current_city = state.current_city
        existing.current_category = state.current_category
        existing.status = state.status
        existing.pause_requested = state.pause_requested
        existing.stop_requested = state.stop_requested
        existing.error = state.error
        existing.finished_at = state.finished_at
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def create_job(
        self,
        *,
        job_id: str,
        country: str,
        target_count: int,
        total_queries: int,
        cities: list[str] | None,
        categories: list[str] | None,
        max_queries: int | None,
    ) -> BulkJob:
        return await self.create(
            BulkJob(
                job_id=job_id,
                country=country,
                target_count=target_count,
                total_queries=total_queries,
                status=SearchStatus.RUNNING,
                cities=cities,
                categories=categories,
                max_queries=max_queries,
            )
        )

    async def sync_control_flags(self, job_id: str, state: BulkJobState) -> None:
        existing = await self.get_by_job_id(job_id)
        if existing is None:
            return
        existing.pause_requested = state.pause_requested
        existing.stop_requested = state.stop_requested
        existing.status = state.status
        existing.finished_at = state.finished_at
        existing.current_city = state.current_city
        existing.current_category = state.current_category
        await self.session.flush()
