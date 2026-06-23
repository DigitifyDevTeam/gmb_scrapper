import logging
import time

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from app.scraper.exceptions import GoogleMapsBlockedError

logger = logging.getLogger(__name__)

FEED_SELECTOR = 'div[role="feed"]'
PLACE_LINK_SELECTOR = 'a[href*="/maps/place"]'
FEED_PLACE_CARD_SELECTOR = f'{FEED_SELECTOR} {PLACE_LINK_SELECTOR}'

BLOCK_URL_FRAGMENTS = (
    "/sorry/",
    "google.com/sorry",
    "consent.google.com/sorry",
)

BLOCK_TEXT_PATTERNS = (
    "unusual traffic",
    "trafic inhabituel",
    "not a robot",
    "pas un robot",
    "detected unusual",
    "activité suspecte",
    "suspicious activity",
)

BLOCK_SELECTORS = (
    "iframe[src*='recaptcha']",
    "iframe[title*='reCAPTCHA']",
    "#captcha",
    "form#captcha-form",
    "div#g-recaptcha",
)

CONSENT_BUTTON_SELECTORS = [
    'button:has-text("Tout accepter")',
    'button:has-text("Accept all")',
    'button:has-text("J\'accepte")',
    'button:has-text("I agree")',
    '[aria-label*="Accept all"]',
    '[aria-label*="Tout accepter"]',
    'form[action*="consent"] button',
]


def is_single_place_url(url: str) -> bool:
    return "/maps/place/" in url


async def dismiss_consent_if_present(page: Page) -> bool:
    """Click through Google's cookie/consent banner when it blocks the map UI."""
    for selector in CONSENT_BUTTON_SELECTORS:
        try:
            button = page.locator(selector).first
            if await button.count() == 0:
                continue
            if not await button.is_visible():
                continue
            await button.click(timeout=3000)
            await page.wait_for_timeout(1500)
            logger.info("Dismissed Google consent dialog")
            return True
        except Exception:
            continue
    return False


async def detect_google_block(page: Page) -> str | None:
    """Return a short reason when Google shows CAPTCHA or anti-bot pages."""
    url = page.url.lower()
    for fragment in BLOCK_URL_FRAGMENTS:
        if fragment in url:
            return "sorry_page"

    for selector in BLOCK_SELECTORS:
        try:
            if await page.locator(selector).count() > 0:
                return "captcha_challenge"
        except Exception:
            continue

    try:
        body_text = (await page.locator("body").inner_text(timeout=2000)).lower()
    except Exception:
        body_text = ""

    for pattern in BLOCK_TEXT_PATTERNS:
        if pattern in body_text:
            return f"block_text:{pattern}"

    return None


async def assert_maps_page_accessible(page: Page) -> None:
    reason = await detect_google_block(page)
    if reason is not None:
        raise GoogleMapsBlockedError(reason)


async def prepare_maps_search_page(page: Page) -> None:
    """Dismiss consent (twice — the banner can appear slightly late) and settle the UI."""
    await dismiss_consent_if_present(page)
    await page.wait_for_timeout(2000)
    await dismiss_consent_if_present(page)
    await assert_maps_page_accessible(page)


async def wait_for_results_feed(page: Page, *, timeout_ms: int = 45_000) -> bool:
    """Wait until search results are visible. Never raises — returns False on timeout."""
    if is_single_place_url(page.url):
        return True

    deadline = time.monotonic() + timeout_ms / 1000
    result_selectors = [
        FEED_SELECTOR,
        FEED_PLACE_CARD_SELECTOR,
        'div[role="main"] a[href*="/maps/place"]',
        "h1.DUwDvf",
    ]

    while time.monotonic() < deadline:
        await dismiss_consent_if_present(page)
        for selector in result_selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() == 0:
                    continue
                await locator.wait_for(state="visible", timeout=2000)
                return True
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue
        await page.wait_for_timeout(1000)

    if is_single_place_url(page.url):
        return True

    logger.warning("Results feed not found within %sms for %s", timeout_ms, page.url)
    return False


async def count_place_cards(page: Page) -> int:
    feed_count = await page.locator(FEED_PLACE_CARD_SELECTOR).count()
    if feed_count > 0:
        return feed_count
    if is_single_place_url(page.url):
        return 1
    main_count = await page.locator('div[role="main"] a[href*="/maps/place"]').count()
    return main_count
