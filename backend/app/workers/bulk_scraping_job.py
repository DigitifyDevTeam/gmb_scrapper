import asyncio
import logging

from app.core.config import get_settings
from app.data.france_bulk import build_france_query_plan
from app.database.session import AsyncSessionLocal
from app.models.enums import SearchStatus
from app.repositories.search_repository import SearchRepository
from app.services.bulk_job_persistence import schedule_sync_bulk_job
from app.workers.job_runner import job_runner
from app.workers.scraping_job import create_search_record, execute_search_scrape

logger = logging.getLogger(__name__)


async def _wait_until_running_or_stop(bulk_job_id: str) -> bool:
    """Block while paused. Returns False when stop is requested."""
    while True:
        state = job_runner.get_bulk_job(bulk_job_id)
        if state is None:
            return False
        if state.stop_requested:
            state.status = SearchStatus.STOPPED
            return False
        if not state.pause_requested:
            if state.status == SearchStatus.PAUSED:
                state.status = SearchStatus.RUNNING
            return True
        state.status = SearchStatus.PAUSED
        await asyncio.sleep(1)


async def run_bulk_scraping_job(
    bulk_job_id: str,
    *,
    country: str,
    target_count: int,
    cities: list[str] | None = None,
    categories: list[str] | None = None,
    max_queries: int | None = None,
    start_from_query_index: int = 0,
) -> None:
    settings = get_settings()
    queries = build_france_query_plan(
        cities=cities,
        categories=categories,
        max_queries=max_queries or settings.bulk_max_queries,
    )
    if not queries:
        raise ValueError("No bulk queries to run")

    job_runner.update_bulk_progress(bulk_job_id, total_queries=len(queries))
    _sync_progress(bulk_job_id)
    logger.info(
        "Starting bulk scrape %s: country=%s target=%s queries=%s resume_from=%s",
        bulk_job_id,
        country,
        target_count,
        len(queries),
        start_from_query_index,
    )

    for index, (city, category) in enumerate(
        queries[start_from_query_index:],
        start=start_from_query_index + 1,
    ):
        bulk_state = job_runner.get_bulk_job(bulk_job_id)
        if bulk_state is None:
            raise ValueError(f"Bulk job {bulk_job_id} not found")

        if bulk_state.stop_requested:
            bulk_state.status = SearchStatus.STOPPED
            break

        if not await _wait_until_running_or_stop(bulk_job_id):
            break

        if bulk_state.prospects_saved >= target_count:
            logger.info(
                "Bulk job %s reached target %s prospects",
                bulk_job_id,
                target_count,
            )
            break

        job_runner.update_bulk_progress(
            bulk_job_id,
            current_city=city,
            current_category=category,
        )
        _sync_progress(bulk_job_id)

        async with AsyncSessionLocal() as session:
            search_repo = SearchRepository(session)
            search = await create_search_record(
                session,
                country=country,
                city=city,
                category=category,
            )
            await search_repo.update_status(search.id, SearchStatus.RUNNING)
            await session.commit()
            search_id = search.id

        try:
            async with AsyncSessionLocal() as session:
                result = await execute_search_scrape(
                    session,
                    search_id,
                    use_global_dedupe=True,
                )
                await session.commit()
        except Exception:
            async with AsyncSessionLocal() as session:
                search_repo = SearchRepository(session)
                await search_repo.update_status(search_id, SearchStatus.FAILED)
                await session.commit()
            raise

        job_runner.update_bulk_progress(
            bulk_job_id,
            found_delta=result.found,
            saved_delta=result.saved_leads,
            skipped_delta=result.skipped_duplicates,
            completed_queries=index,
        )
        _sync_progress(bulk_job_id)

        logger.info(
            "Bulk %s progress %s/%s | %s/%s | saved=%s total_saved=%s",
            bulk_job_id,
            index,
            len(queries),
            city,
            category,
            result.saved,
            job_runner.get_bulk_job(bulk_job_id).prospects_saved if job_runner.get_bulk_job(bulk_job_id) else 0,
        )

        if index < len(queries):
            bulk_state = job_runner.get_bulk_job(bulk_job_id)
            if bulk_state is not None and bulk_state.stop_requested:
                bulk_state.status = SearchStatus.STOPPED
                break
            if not await _wait_until_running_or_stop(bulk_job_id):
                break
            await asyncio.sleep(settings.bulk_delay_between_searches_seconds)

    final_state = job_runner.get_bulk_job(bulk_job_id)
    if final_state is not None:
        logger.info(
            "Bulk job %s finished: saved=%s skipped=%s queries=%s/%s",
            bulk_job_id,
            final_state.prospects_saved,
            final_state.prospects_skipped_duplicates,
            final_state.completed_queries,
            final_state.total_queries,
        )


def _sync_progress(bulk_job_id: str) -> None:
    state = job_runner.get_bulk_job(bulk_job_id)
    if state is not None:
        schedule_sync_bulk_job(state)
