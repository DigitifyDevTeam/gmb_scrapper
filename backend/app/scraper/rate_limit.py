import asyncio
import random

from app.core.config import Settings


async def scraper_action_delay(settings: Settings) -> None:
    """Human-like pause between card clicks and similar actions."""
    jitter = random.randint(0, settings.scraper_request_delay_jitter_ms)
    delay_ms = settings.scraper_request_delay_ms + jitter
    await asyncio.sleep(delay_ms / 1000)


async def scraper_page_settle_delay(settings: Settings) -> None:
    """Let the Maps UI settle after navigation before scraping."""
    jitter = random.randint(0, settings.scraper_page_settle_jitter_ms)
    delay_ms = settings.scraper_page_settle_ms + jitter
    await asyncio.sleep(delay_ms / 1000)


async def scraper_scroll_delay(settings: Settings) -> None:
    """Pause while scrolling the results feed."""
    jitter = random.randint(0, settings.scraper_scroll_pause_jitter_ms)
    delay_ms = settings.scraper_scroll_pause_ms + jitter
    await asyncio.sleep(delay_ms / 1000)


async def bulk_search_delay(settings: Settings) -> None:
    """Pause between bulk city/category queries."""
    jitter = random.uniform(0, settings.bulk_delay_jitter_seconds)
    delay_seconds = settings.bulk_delay_between_searches_seconds + jitter
    await asyncio.sleep(delay_seconds)


def bulk_failure_cooldown_seconds(settings: Settings, consecutive_failures: int) -> float:
    """Exponential backoff after failed bulk queries."""
    if consecutive_failures <= 0:
        return 0.0
    multiplier = 2 ** (consecutive_failures - 1)
    cooldown = settings.bulk_failure_cooldown_seconds * multiplier
    return min(cooldown, settings.bulk_failure_cooldown_max_seconds)
