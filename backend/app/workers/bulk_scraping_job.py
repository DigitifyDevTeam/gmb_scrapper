import asyncio
import logging

from app.core.config import get_settings
from app.data.france_bulk import build_france_query_plan
from app.database.session import AsyncSessionLocal
from app.models.enums import SearchStatus
from app.repositories.search_repository import SearchRepository
from app.scraper.exceptions import BulkJobCancelledError, GoogleMapsBlockedError
from app.scraper.rate_limit import bulk_failure_cooldown_seconds, bulk_search_delay
from app.services.bulk_job_persistence import schedule_sync_bulk_job
from app.workers.job_runner import job_runner
from app.workers.scraping_job import create_search_record, execute_search_scrape

logger = logging.getLogger(__name__)

_BLOCK_PAUSE_MESSAGE = (
    "Google blocked automated access. Job paused. Set SCRAPER_HEADLESS=false, solve the "
    "challenge in the browser if needed, then resume after the cooldown."
)


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


def _pause_bulk_job(bulk_job_id: str, message: str) -> None:
    state = job_runner.get_bulk_job(bulk_job_id)
    if state is None:
        return
    state.pause_requested = True
    state.status = SearchStatus.PAUSED
    state.error = message
    schedule_sync_bulk_job(state)


async def _handle_google_block(bulk_job_id: str, settings) -> None:
    logger.warning("Bulk job %s detected Google block — pausing for cooldown", bulk_job_id)
    _pause_bulk_job(bulk_job_id, _BLOCK_PAUSE_MESSAGE)
    await asyncio.sleep(settings.bulk_blocked_cooldown_seconds)
    if not await _wait_until_running_or_stop(bulk_job_id):
        return
    logger.info("Bulk job %s resumed after Google block cooldown", bulk_job_id)


async def _cooldown_after_failure(
    bulk_job_id: str,
    settings,
    *,
    consecutive_failures: int,
) -> bool:
    cooldown = bulk_failure_cooldown_seconds(settings, consecutive_failures)
    if cooldown > 0:
        logger.warning(
            "Bulk job %s backing off for %.0fs after %s consecutive failures",
            bulk_job_id,
            cooldown,
            consecutive_failures,
        )
        await asyncio.sleep(cooldown)

    if consecutive_failures >= settings.bulk_max_consecutive_failures:
        _pause_bulk_job(
            bulk_job_id,
            f"Paused after {consecutive_failures} consecutive failed queries. "
            "Check logs, increase delays, then resume.",
        )
        return await _wait_until_running_or_stop(bulk_job_id)

    return True


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

    consecutive_failures = 0
    current_search_id: int | None = None

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
            current_search_id = search_id

        try:
            async with AsyncSessionLocal() as session:
                result = await execute_search_scrape(
                    session,
                    search_id,
                    bulk_job_id=bulk_job_id,
                )
                await session.commit()
        except BulkJobCancelledError:
            bulk_state = job_runner.get_bulk_job(bulk_job_id)
            if bulk_state is None or not bulk_state.stop_requested:
                logger.warning(
                    "Bulk %s query %s/%s hit cancel without stop request — skipping query",
                    bulk_job_id,
                    index,
                    len(queries),
                )
                async with AsyncSessionLocal() as session:
                    search_repo = SearchRepository(session)
                    await search_repo.update_status(search_id, SearchStatus.FAILED)
                    await session.commit()
                current_search_id = None
                continue

            logger.info(
                "Bulk %s query %s/%s cancelled for %s / %s",
                bulk_job_id,
                index,
                len(queries),
                city,
                category,
            )
            async with AsyncSessionLocal() as session:
                search_repo = SearchRepository(session)
                await search_repo.update_status(search_id, SearchStatus.STOPPED)
                await session.commit()
            current_search_id = None
            break
        except asyncio.CancelledError:
            bulk_state = job_runner.get_bulk_job(bulk_job_id)
            if (
                bulk_state is not None
                and bulk_state.stop_requested
                and current_search_id is not None
            ):
                async with AsyncSessionLocal() as session:
                    search_repo = SearchRepository(session)
                    await search_repo.update_status(current_search_id, SearchStatus.STOPPED)
                    await session.commit()
            raise
        except GoogleMapsBlockedError as exc:
            logger.exception(
                "Bulk %s query %s/%s blocked for %s / %s",
                bulk_job_id,
                index,
                len(queries),
                city,
                category,
            )
            async with AsyncSessionLocal() as session:
                search_repo = SearchRepository(session)
                await search_repo.update_status(search_id, SearchStatus.FAILED)
                await session.commit()
            job_runner.update_bulk_progress(
                bulk_job_id,
                completed_queries=index,
            )
            _sync_progress(bulk_job_id)
            bulk_state = job_runner.get_bulk_job(bulk_job_id)
            if bulk_state is not None:
                bulk_state.error = str(exc)
            consecutive_failures += 1
            await _handle_google_block(bulk_job_id, settings)
            bulk_state = job_runner.get_bulk_job(bulk_job_id)
            if bulk_state is None or bulk_state.stop_requested:
                if bulk_state is not None:
                    bulk_state.status = SearchStatus.STOPPED
                break
            continue
        except Exception as exc:
            logger.exception(
                "Bulk %s query %s/%s failed for %s / %s",
                bulk_job_id,
                index,
                len(queries),
                city,
                category,
            )
            async with AsyncSessionLocal() as session:
                search_repo = SearchRepository(session)
                await search_repo.update_status(search_id, SearchStatus.FAILED)
                await session.commit()
            job_runner.update_bulk_progress(
                bulk_job_id,
                completed_queries=index,
            )
            _sync_progress(bulk_job_id)
            bulk_state = job_runner.get_bulk_job(bulk_job_id)
            if bulk_state is not None:
                bulk_state.error = str(exc) or repr(exc)
            consecutive_failures += 1
            if index < len(queries):
                bulk_state = job_runner.get_bulk_job(bulk_job_id)
                if bulk_state is not None and bulk_state.stop_requested:
                    bulk_state.status = SearchStatus.STOPPED
                    break
                if not await _cooldown_after_failure(
                    bulk_job_id,
                    settings,
                    consecutive_failures=consecutive_failures,
                ):
                    break
            continue

        consecutive_failures = 0
        current_search_id = None
        job_runner.update_bulk_progress(
            bulk_job_id,
            found_delta=result.found,
            saved_delta=result.saved_leads,
            saved_with_website_delta=result.saved_with_website,
            saved_total_delta=result.saved,
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
            await bulk_search_delay(settings)

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
