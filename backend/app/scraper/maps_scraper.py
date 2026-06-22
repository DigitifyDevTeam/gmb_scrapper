import asyncio
import logging
import random
from urllib.parse import quote_plus

from app.core.config import get_settings
from app.scraper.business_parser import RawBusiness
from app.scraper.extraction_engine import ExtractionEngine
from app.scraper.playwright_manager import PlaywrightManager
from app.scraper.playwright_runner import run_playwright_task
from app.scraper.scroll_engine import ScrollEngine
from app.utils.url import normalize_maps_url

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

    async def scrape(self, category: str, city: str, country: str) -> list[RawBusiness]:
        url = self.build_search_url(category, city, country)
        logger.info("Starting Google Maps scrape: %s", url)
        locale = self._locale_for_country(country)

        async def scrape_maps() -> list[RawBusiness]:
            async with self.playwright_manager.session(locale=locale) as (_, _, page):
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(2000)

                await self.scroll_engine.scroll_results_feed(
                    page,
                    max_results=self.settings.scraper_max_results,
                )
                businesses = await self.extraction_engine.extract_businesses(
                    page,
                    max_results=self.settings.scraper_max_results,
                )

            logger.info("Scrape completed with %s businesses", len(businesses))
            return businesses

        return await run_playwright_task(scrape_maps)

    async def scrape_testimonials(self, maps_urls: list[str], country: str) -> dict[str, list[dict]]:
        unique_urls = []
        seen: set[str] = set()
        for url in maps_urls:
            normalized = normalize_maps_url(url)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_urls.append(normalized)

        if not unique_urls:
            return {}

        locale = self._locale_for_country(country)
        logger.info("Fetching testimonials for %s leads", len(unique_urls))

        async def fetch_testimonials() -> dict[str, list[dict]]:
            results: dict[str, list[dict]] = {}
            async with self.playwright_manager.session(locale=locale) as (_, _, page):
                for maps_url in unique_urls:
                    try:
                        await page.goto(maps_url, wait_until="domcontentloaded", timeout=60000)
                        await page.wait_for_timeout(2000)
                        testimonials = await self.extraction_engine.extract_testimonials(page)
                        results[maps_url] = [item.to_dict() for item in testimonials]
                    except Exception as exc:
                        logger.warning("Failed to fetch testimonials for %s: %s", maps_url, exc)
                        results[maps_url] = []

                    await asyncio.sleep(
                        (self.settings.scraper_request_delay_ms + random.randint(0, 300)) / 1000
                    )
            return results

        return await run_playwright_task(fetch_testimonials)
