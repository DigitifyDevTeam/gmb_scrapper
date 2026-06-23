import asyncio
import logging
from datetime import datetime, timezone

from app.database.session import AsyncSessionLocal
from app.models.bulk_job import BulkJob
from app.models.enums import SearchStatus
from app.repositories.bulk_job_repository import BulkJobRepository
from app.repositories.search_repository import SearchRepository
from app.workers.job_runner import BulkJobState, job_runner

logger = logging.getLogger(__name__)


def schedule_sync_bulk_job(state: BulkJobState) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(sync_bulk_job_state(state))


async def sync_bulk_job_state(state: BulkJobState) -> None:
    async with AsyncSessionLocal() as session:
        repo = BulkJobRepository(session)
        await repo.upsert_from_state(state)
        await session.commit()


def bulk_job_to_state(job: BulkJob) -> BulkJobState:
    return BulkJobState(
        job_id=job.job_id,
        country=job.country,
        target_count=job.target_count,
        status=job.status,
        total_queries=job.total_queries,
        completed_queries=job.completed_queries,
        prospects_found=job.prospects_found,
        prospects_saved=job.prospects_saved,
        prospects_saved_with_website=job.prospects_saved_with_website,
        prospects_saved_total=job.prospects_saved_total,
        prospects_skipped_duplicates=job.prospects_skipped_duplicates,
        current_city=job.current_city,
        current_category=job.current_category,
        pause_requested=job.pause_requested,
        stop_requested=job.stop_requested,
        error=job.error,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


async def recover_interrupted_bulk_jobs() -> None:
    from app.workers.bulk_scraping_job import run_bulk_scraping_job

    async with AsyncSessionLocal() as session:
        bulk_repo = BulkJobRepository(session)
        search_repo = SearchRepository(session)
        await bulk_repo.finalize_inconsistent_jobs()
        interrupted = await bulk_repo.list_by_status([SearchStatus.RUNNING, SearchStatus.PAUSED])

        for db_job in interrupted:
            if db_job.stop_requested:
                logger.warning(
                    "Marking bulk job %s as stopped (stop was requested before shutdown)",
                    db_job.job_id,
                )
                db_job.status = SearchStatus.STOPPED
                db_job.pause_requested = False
                if db_job.finished_at is None:
                    db_job.finished_at = datetime.now(timezone.utc)
                continue

            logger.warning(
                "Recovering interrupted bulk job %s (completed_queries=%s, status=%s)",
                db_job.job_id,
                db_job.completed_queries,
                db_job.status,
            )
            state = bulk_job_to_state(db_job)
            job_runner.register_bulk_job(state)

            if db_job.status == SearchStatus.PAUSED:
                state.pause_requested = True
                continue

            state.status = SearchStatus.RUNNING
            state.pause_requested = False

            async def job_wrapper(
                job_id: str = db_job.job_id,
                country: str = db_job.country,
                target_count: int = db_job.target_count,
                cities: list[str] | None = db_job.cities,
                categories: list[str] | None = db_job.categories,
                max_queries: int | None = db_job.max_queries,
                start_from_query_index: int = db_job.completed_queries,
            ) -> None:
                await run_bulk_scraping_job(
                    job_id,
                    country=country,
                    target_count=target_count,
                    cities=cities,
                    categories=categories,
                    max_queries=max_queries,
                    start_from_query_index=start_from_query_index,
                )

            job_runner.start_bulk_job_task(state, job_wrapper)

        await search_repo.mark_running_as_failed()
        await session.commit()
