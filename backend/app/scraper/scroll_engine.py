import asyncio
import logging

from playwright.async_api import Page

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ScrollEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def scroll_results_feed(self, page: Page, max_results: int | None = None) -> int:
        max_results = max_results or self.settings.scraper_max_results
        feed_selector = 'div[role="feed"]'
        await page.wait_for_selector(feed_selector, timeout=30000)

        previous_count = 0
        stable_rounds = 0

        while stable_rounds < self.settings.scraper_scroll_stable_rounds:
            cards = await page.locator('div[role="feed"] a[href*="/maps/place"]').count()
            if cards >= max_results:
                logger.info("Reached max results cap: %s", max_results)
                break

            if cards == previous_count:
                stable_rounds += 1
            else:
                stable_rounds = 0
                previous_count = cards

            await page.locator(feed_selector).evaluate(
                "(el) => { el.scrollTop = el.scrollHeight; }"
            )
            await asyncio.sleep(self.settings.scraper_scroll_pause_ms / 1000)

        final_count = await page.locator('div[role="feed"] a[href*="/maps/place"]').count()
        return min(final_count, max_results)
