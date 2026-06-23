import logging
from urllib.parse import quote_plus

from playwright.async_api import Page

from app.core.config import get_settings
from app.scraper.business_parser import RawBusiness
from app.scraper.exceptions import BulkJobCancelledError
from app.scraper.extraction_engine import ExtractionEngine
from app.scraper.maps_ui import assert_maps_page_accessible, prepare_maps_search_page, wait_for_results_feed
from app.scraper.playwright_manager import PlaywrightManager
from app.scraper.playwright_runner import run_playwright_task
from app.scraper.rate_limit import scraper_action_delay, scraper_page_settle_delay
from app.scraper.scroll_engine import ScrollEngine
from app.scraper.testimonial import TestimonialFetchTarget
from app.utils.url import resolve_maps_navigation_url
from app.workers.bulk_cancel import is_bulk_cancel_requested

logger = logging.getLogger(__name__)


class MapsScraper:
    """
    Google Maps scraper using Playwright.

    Note: Automated scraping may violate Google Maps Terms of Service.
    Use responsibly with rate limiting. No CAPTCHA bypass is implemented.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.playwright_manager = PlaywrightManager()
        self.scroll_engine = ScrollEngine()
        self.extraction_engine = ExtractionEngine()

    def build_search_url(self, category: str, city: str, country: str) -> str:
        query = quote_plus(f"{category} {city} {country}")
        return f"https://www.google.com/maps/search/{query}"

    def _locale_for_country(self, country: str) -> str:
        normalized = country.strip().lower()
        if normalized in {"france", "fr", "français"}:
            return "fr-FR"
        return "en-US"

    async def scrape(
        self,
        category: str,
        city: str,
        country: str,
        *,
        bulk_job_id: str | None = None,
    ) -> list[RawBusiness]:
        url = self.build_search_url(category, city, country)
        logger.info("Starting Google Maps scrape: %s", url)
        locale = self._locale_for_country(country)

        async def scrape_maps() -> list[RawBusiness]:
            async with self.playwright_manager.session(locale=locale) as (_, _, page):
                businesses = await self._scrape_page(page, url, bulk_job_id=bulk_job_id)

            logger.info("Scrape completed with %s businesses", len(businesses))
            return businesses

        return await run_playwright_task(scrape_maps)

    async def _scrape_page(
        self,
        page: Page,
        url: str,
        *,
        bulk_job_id: str | None = None,
    ) -> list[RawBusiness]:
        if bulk_job_id and is_bulk_cancel_requested(bulk_job_id):
            raise BulkJobCancelledError(bulk_job_id)

        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await scraper_page_settle_delay(self.settings)
        await prepare_maps_search_page(page)

        ready = await wait_for_results_feed(page)
        if not ready:
            logger.warning("No results on first load for %s — reloading once", url)
            await page.reload(wait_until="domcontentloaded", timeout=60000)
            await scraper_page_settle_delay(self.settings)
            await prepare_maps_search_page(page)
            ready = await wait_for_results_feed(page)

        if not ready:
            await assert_maps_page_accessible(page)
            logger.warning("No Google Maps results for %s — skipping query", url)
            return []

        await self.scroll_engine.scroll_results_feed(
            page,
            max_results=self.settings.scraper_max_results,
            bulk_job_id=bulk_job_id,
        )
        return await self.extraction_engine.extract_businesses(
            page,
            max_results=self.settings.scraper_max_results,
            bulk_job_id=bulk_job_id,
        )

    async def scrape_testimonials(
        self,
        targets: list[TestimonialFetchTarget],
        country: str,
    ) -> dict[str, list[dict]]:
        unique_targets: list[TestimonialFetchTarget] = []
        seen_keys: set[str] = set()
        for target in targets:
            if target.place_key in seen_keys:
                continue
            seen_keys.add(target.place_key)
            unique_targets.append(target)

        if not unique_targets:
            return {}

        locale = self._locale_for_country(country)
        logger.info("Fetching testimonials for %s leads", len(unique_targets))

        async def fetch_testimonials() -> dict[str, list[dict]]:
            results: dict[str, list[dict]] = {}
            async with self.playwright_manager.session(locale=locale) as (_, _, page):
                for target in unique_targets:
                    try:
                        await page.goto(
                            target.navigation_url,
                            wait_until="domcontentloaded",
                            timeout=60000,
                        )
                        await scraper_page_settle_delay(self.settings)
                        await prepare_maps_search_page(page)
                        await assert_maps_page_accessible(page)
                        if not await wait_for_results_feed(page):
                            logger.warning(
                                "Maps place did not load for testimonials: %s",
                                target.business_name,
                            )
                            results[target.place_key] = []
                            continue
                        testimonials = await self.extraction_engine.extract_testimonials(
                            page,
                            expected_business_name=target.business_name,
                        )
                        results[target.place_key] = [item.to_dict() for item in testimonials]
                    except Exception as exc:
                        logger.warning(
                            "Failed to fetch testimonials for %s: %s",
                            target.business_name,
                            exc,
                        )
                        results[target.place_key] = []

                    await scraper_action_delay(self.settings)
            return results

        return await run_playwright_task(fetch_testimonials)
