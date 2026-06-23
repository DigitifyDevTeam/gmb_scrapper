import logging

from playwright.async_api import Page

from app.core.config import get_settings
from app.scraper.exceptions import BulkJobCancelledError
from app.scraper.maps_ui import FEED_SELECTOR, count_place_cards, wait_for_results_feed
from app.scraper.rate_limit import scraper_scroll_delay
from app.workers.bulk_cancel import is_bulk_cancel_requested

logger = logging.getLogger(__name__)


class ScrollEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def scroll_results_feed(
        self,
        page: Page,
        max_results: int | None = None,
        *,
        bulk_job_id: str | None = None,
    ) -> int:
        max_results = max_results or self.settings.scraper_max_results

        ready = await wait_for_results_feed(page)
        if not ready:
            logger.warning("Skipping scroll — no results feed on %s", page.url)
            return 0

        initial_count = await count_place_cards(page)
        if initial_count <= 1:
            return min(initial_count, max_results)

        feed = page.locator(FEED_SELECTOR)
        if await feed.count() == 0:
            return min(initial_count, max_results)

        previous_count = 0
        stable_rounds = 0

        while stable_rounds < self.settings.scraper_scroll_stable_rounds:
            if bulk_job_id and is_bulk_cancel_requested(bulk_job_id):
                raise BulkJobCancelledError(bulk_job_id)
            cards = await count_place_cards(page)
            if cards >= max_results:
                logger.info("Reached max results cap: %s", max_results)
                break

            if cards == previous_count:
                stable_rounds += 1
            else:
                stable_rounds = 0
                previous_count = cards

            await feed.evaluate("(el) => { el.scrollTop = el.scrollHeight; }")
            await scraper_scroll_delay(self.settings)

        final_count = await count_place_cards(page)
        return min(final_count, max_results)
