from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.core.config import get_settings

_LOCALE_CONTEXT: dict[str, dict[str, object]] = {
    "fr-FR": {
        "timezone_id": "Europe/Paris",
        "extra_http_headers": {"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"},
    },
    "en-US": {
        "timezone_id": "America/New_York",
        "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"},
    },
}


class PlaywrightManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._browser: Browser | None = None

    def _context_options(self, locale: str) -> dict[str, object]:
        locale_options = _LOCALE_CONTEXT.get(locale, _LOCALE_CONTEXT["en-US"])
        return {
            "viewport": {"width": 1440, "height": 900},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "locale": locale,
            "timezone_id": locale_options["timezone_id"],
            "extra_http_headers": locale_options["extra_http_headers"],
        }

    @asynccontextmanager
    async def session(
        self, *, locale: str = "en-US"
    ) -> AsyncGenerator[tuple[Browser, BrowserContext, Page], None]:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.settings.scraper_headless)
            context = await browser.new_context(**self._context_options(locale))
            page = await context.new_page()
            try:
                yield browser, context, page
            finally:
                await context.close()
                await browser.close()
