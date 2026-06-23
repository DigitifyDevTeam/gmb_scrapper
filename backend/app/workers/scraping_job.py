import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.models.enums import SearchStatus
from app.models.prospect import Prospect
from app.models.search import Search
from app.repositories.prospect_repository import ProspectRepository
from app.repositories.search_repository import SearchRepository
from app.scraper.exceptions import BulkJobCancelledError
from app.scraper.maps_scraper import MapsScraper
from app.services.normalization_service import NormalizationService
from app.services.prospect_record_service import build_prospect_from_scrape
from app.services.website_detection_service import WebsiteDetectionService
from app.utils.prospect_identity import build_prospect_dedupe_key
from app.workers.bulk_cancel import is_bulk_cancel_requested
from app.workers.job_runner import job_runner
from app.workers.scrape_result import ScrapeRunResult

logger = logging.getLogger(__name__)


async def execute_search_scrape(
    session: AsyncSession,
    search_id: int,
    *,
    progress_job_id: str | None = None,
    bulk_job_id: str | None = None,
) -> ScrapeRunResult:
    scraper = MapsScraper()
    normalization_service = NormalizationService()
    detection_service = WebsiteDetectionService()
    search_repo = SearchRepository(session)
    prospect_repo = ProspectRepository(session)

    search = await search_repo.get_by_id(search_id)
    if search is None:
        raise ValueError(f"Search {search_id} not found")

    raw_businesses = await scraper.scrape(
        category=search.category,
        city=search.city,
        country=search.country,
        bulk_job_id=bulk_job_id,
    )
    if bulk_job_id and is_bulk_cancel_requested(bulk_job_id):
        raise BulkJobCancelledError(bulk_job_id)
    if progress_job_id is not None:
        job_runner.update_progress(progress_job_id, found=len(raw_businesses))

    normalized = normalization_service.normalize_batch(raw_businesses, search.country)
    enriched = await detection_service.enrich_batch(normalized)

    prospects_to_save: list[Prospect] = []
    skipped_duplicates = 0
    saved_with_website_minimal = 0
    seen_dedupe_keys: set[str] = set()
    for business, detection in enriched:
        if bulk_job_id and is_bulk_cancel_requested(bulk_job_id):
            raise BulkJobCancelledError(bulk_job_id)
        dedupe_key, _ = build_prospect_dedupe_key(
            business_name=business.business_name,
            address=business.address,
            phone=business.phone,
            maps_url=business.maps_url,
            country=search.country,
        )

        if dedupe_key in seen_dedupe_keys:
            skipped_duplicates += 1
            continue

        exists = await prospect_repo.exists_globally(
            business_name=business.business_name,
            address=business.address,
            phone=business.phone,
            maps_url=business.maps_url,
            country=search.country,
        )
        if exists:
            skipped_duplicates += 1
            continue

        seen_dedupe_keys.add(dedupe_key)

        prospect = build_prospect_from_scrape(
            search_id=search_id,
            business=business,
            detection=detection,
            country=search.country,
            city=search.city,
        )
        if detection.has_website:
            saved_with_website_minimal += 1
        prospects_to_save.append(prospect)

    lead_maps_urls = [
        prospect.maps_url
        for prospect in prospects_to_save
        if not prospect.has_website and prospect.maps_url
    ]
    if lead_maps_urls:
        testimonials_by_url = await scraper.scrape_testimonials(lead_maps_urls, search.country)
        for prospect in prospects_to_save:
            if not prospect.has_website and prospect.maps_url:
                prospect.testimonials = testimonials_by_url.get(prospect.maps_url) or None

    if prospects_to_save:
        prospects_to_save = await prospect_repo.create_many_deduped(prospects_to_save)

    await search_repo.update_status(search_id, SearchStatus.COMPLETED)
    if progress_job_id is not None:
        job_runner.update_progress(progress_job_id, saved=len(prospects_to_save))

    saved_leads = len(prospects_to_save) - saved_with_website_minimal

    logger.info(
        "Search %s completed: found=%s saved=%s leads=%s dedupe_skipped=%s minimal_with_website=%s",
        search_id,
        len(raw_businesses),
        len(prospects_to_save),
        saved_leads,
        skipped_duplicates,
        saved_with_website_minimal,
    )
    return ScrapeRunResult(
        found=len(raw_businesses),
        saved=len(prospects_to_save),
        skipped_duplicates=skipped_duplicates,
        skipped_has_website=saved_with_website_minimal,
        saved_leads=saved_leads,
    )


async def run_scraping_job(search_id: int) -> None:
    job_id = f"search-{search_id}"

    async with AsyncSessionLocal() as session:
        search_repo = SearchRepository(session)
        try:
            await execute_search_scrape(session, search_id, progress_job_id=job_id)
            await session.commit()

            job = job_runner.get_job(job_id)
            if job is not None:
                job.status = SearchStatus.COMPLETED
        except Exception:
            await search_repo.update_status(search_id, SearchStatus.FAILED)
            await session.commit()
            job = job_runner.get_job(job_id)
            if job is not None:
                job.status = SearchStatus.FAILED
            raise


async def create_search_record(
    session: AsyncSession,
    *,
    country: str,
    city: str,
    category: str,
) -> Search:
    search_repo = SearchRepository(session)
    search = await search_repo.create(
        Search(
            country=country,
            city=city,
            category=category,
            status=SearchStatus.PENDING,
        )
    )
    await session.flush()
    return search
