import asyncio
import logging

from playwright.async_api import Locator, Page

from app.core.config import get_settings
from app.scraper.business_parser import BusinessParser, RawBusiness
from app.scraper.exceptions import BulkJobCancelledError
from app.scraper.maps_ui import FEED_PLACE_CARD_SELECTOR, count_place_cards, is_single_place_url
from app.scraper.rate_limit import scraper_action_delay
from app.workers.bulk_cancel import is_bulk_cancel_requested
from app.scraper.testimonial import (
    Testimonial,
    business_names_match,
    parse_rating_from_aria,
)
from app.utils.phone import extract_phone_from_data_item_id
from app.utils.prospect_identity import pick_best_maps_source_url
from app.utils.url import parse_website_href

logger = logging.getLogger(__name__)

PLACE_PANEL_SELECTOR = 'div[role="main"]'
WEBSITE_LINK_SELECTORS = (
    'a[data-item-id="authority"]',
    'button[data-item-id="authority"]',
    'a[data-item-id^="authority:"]',
    'button[data-item-id^="authority:"]',
    'a[aria-label*="site web" i]',
    'a[aria-label*="website" i]',
    'button[aria-label*="site web" i]',
    'button[aria-label*="website" i]',
    'a[data-tooltip*="site web" i]',
    'a[data-tooltip*="website" i]',
    'a[href*="/url?q="]',
)


class ExtractionEngine:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.parser = BusinessParser()

    async def extract_businesses(
        self,
        page: Page,
        max_results: int,
        *,
        bulk_job_id: str | None = None,
    ) -> list[RawBusiness]:
        card_locator = page.locator(FEED_PLACE_CARD_SELECTOR)
        card_count = await card_locator.count()
        total_count = min(await count_place_cards(page), max_results)

        if total_count == 0:
            return []

        businesses: list[RawBusiness] = []
        seen_keys: set[str] = set()

        # Google sometimes lands directly on a single place page (no results feed).
        if card_count == 0 and is_single_place_url(page.url):
            business = await self._extract_single_place_page(page)
            if business is not None:
                businesses.append(business)
            return businesses

        count = min(card_count, max_results)
        for index in range(count):
            if bulk_job_id and is_bulk_cancel_requested(bulk_job_id):
                raise BulkJobCancelledError(bulk_job_id)
            try:
                card = card_locator.nth(index)
                business = await self._extract_card(page, card)
                if business is None:
                    continue
                key = self.parser.dedupe_key(business)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                businesses.append(business)
            except Exception as exc:
                logger.warning("Failed to extract card %s: %s", index, exc)

            await scraper_action_delay(self.settings)

        return businesses

    async def _extract_single_place_page(self, page: Page) -> RawBusiness | None:
        await self._wait_for_place_details(page)
        return self.parser.parse_listing_card(
            {
                "business_name": await self._first_text(page, ["h1.DUwDvf", "h1"]),
                "category": await self._first_text(
                    page,
                    ["button.DkEaL", 'button[jsaction*="category"]'],
                ),
                "address": await self._button_text(page, "address"),
                "phone": await self._phone_from_page(page),
                "website": await self._website_from_page(page),
                "rating": await self._rating_from_page(page),
                "review_count": await self._review_count_from_page(page),
                "maps_url": page.url,
            }
        )

    async def _extract_card(self, page: Page, card: Locator) -> RawBusiness | None:
        card_href = await card.get_attribute("href")
        await card.scroll_into_view_if_needed()
        await card.click()
        await self._wait_for_place_details(page)

        name = await self._first_text(
            page,
            [
                "h1.DUwDvf",
                "h1",
                '[data-item-id="title"]',
            ],
        )
        category = await self._first_text(
            page,
            [
                "button.DkEaL",
                'button[jsaction*="category"]',
            ],
        )
        address = await self._button_text(page, "address")
        phone = await self._phone_from_page(page)
        website = await self._website_from_page(page)
        rating_text = await self._rating_from_page(page)
        review_text = await self._review_count_from_page(page)
        maps_url = pick_best_maps_source_url(card_href, page.url)

        if not name:
            name = await card.inner_text()
            name = name.split("\n")[0].strip() if name else None

        return self.parser.parse_listing_card(
            {
                "business_name": name,
                "category": category,
                "address": address,
                "phone": phone,
                "website": website,
                "rating": rating_text,
                "review_count": review_text,
                "maps_url": maps_url,
            }
        )

    async def _first_text(self, page: Page, selectors: list[str]) -> str | None:
        for selector in selectors:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                text = (await locator.inner_text()).strip()
                if text:
                    return text
                aria = await locator.get_attribute("aria-label")
                if aria:
                    return aria.strip()
        return None

    async def _wait_for_place_details(self, page: Page) -> None:
        try:
            await page.wait_for_selector("h1.DUwDvf, h1", timeout=6000)
        except Exception:
            pass

        detail_selectors = (
            'button[data-item-id="address"]',
            'a[data-item-id="address"]',
            'button[data-item-id^="phone:tel:"]',
            'a[data-item-id^="phone:tel:"]',
            'button[data-item-id="phone"]',
            'a[data-item-id="authority"]',
            'button[data-item-id="authority"]',
        )
        for selector in detail_selectors:
            try:
                await page.wait_for_selector(selector, timeout=3000)
                break
            except Exception:
                continue

        await page.wait_for_timeout(self.settings.scraper_place_details_settle_ms)
        await self._scroll_place_details_panel(page)

    async def _scroll_place_details_panel(self, page: Page) -> None:
        panels = page.locator(f"{PLACE_PANEL_SELECTOR} div.m6QErb.DxyBCb")
        if await panels.count() == 0:
            panels = page.locator(f"{PLACE_PANEL_SELECTOR} div.m6QErb")
        if await panels.count() == 0:
            return

        panel = panels.first
        try:
            await panel.evaluate(
                "(el) => { el.scrollTop = Math.min(el.scrollHeight, 900); }"
            )
            await page.wait_for_timeout(400)
            await panel.evaluate("(el) => { el.scrollTop = 0; }")
            await page.wait_for_timeout(300)
        except Exception:
            return

    async def _button_text(self, page: Page, data_item_id: str) -> str | None:
        locator = page.locator(f'button[data-item-id="{data_item_id}"]')
        if await locator.count() == 0:
            locator = page.locator(f'a[data-item-id="{data_item_id}"]')
        if await locator.count() == 0:
            locator = page.locator(f'[data-item-id^="{data_item_id}:"]')
        if await locator.count() == 0:
            return None

        element = locator.first
        data_item = await element.get_attribute("data-item-id")
        if data_item_id == "phone":
            phone = extract_phone_from_data_item_id(data_item)
            if phone:
                return phone

        aria = await element.get_attribute("aria-label")
        if aria:
            return self._strip_field_prefix(aria.strip())
        text = (await element.inner_text()).strip()
        return self._strip_field_prefix(text) if text else None

    async def _phone_from_page(self, page: Page) -> str | None:
        phone_locators = [
            page.locator('button[data-item-id^="phone:tel:"]'),
            page.locator('a[data-item-id^="phone:tel:"]'),
            page.locator('button[data-item-id="phone"]'),
            page.locator('a[data-item-id="phone"]'),
            page.locator('button[data-tooltip*="phone" i]'),
            page.locator('button[data-tooltip*="téléphone" i]'),
            page.locator('a[href^="tel:"]'),
        ]

        for locator in phone_locators:
            if await locator.count() == 0:
                continue
            element = locator.first

            data_item = await element.get_attribute("data-item-id")
            phone = extract_phone_from_data_item_id(data_item)
            if phone:
                return phone

            href = await element.get_attribute("href")
            if href and href.lower().startswith("tel:"):
                return href[4:].strip()

            aria = await element.get_attribute("aria-label")
            if aria:
                cleaned = self._strip_field_prefix(aria.strip())
                if cleaned:
                    return cleaned

            text = (await element.inner_text()).strip()
            if text:
                cleaned = self._strip_field_prefix(text)
                if cleaned:
                    return cleaned

        return None

    async def _rating_from_page(self, page: Page) -> str | None:
        aria_selectors = [
            'span[role="img"][aria-label*="stars"]',
            'span[role="img"][aria-label*="étoiles"]',
            'span[role="img"][aria-label*="etoiles"]',
            'span[role="img"][aria-label*="star"]',
            'span[role="img"][aria-label*="étoile"]',
        ]
        for selector in aria_selectors:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            aria = await locator.get_attribute("aria-label")
            if aria:
                return aria.strip()

        text_selectors = [
            "div.F7nice span[aria-hidden='true']",
            'div.F7nice span[aria-hidden="true"]',
            "div.jANrlb div.fontDisplayLarge",
        ]
        for selector in text_selectors:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            text = (await locator.inner_text()).strip()
            if text:
                return text

        return None

    async def _review_count_from_page(self, page: Page) -> str | None:
        review_selectors = [
            'button[aria-label*="reviews"]',
            'button[aria-label*="avis"]',
            'button[aria-label*="review"]',
            'span[aria-label*="reviews"]',
            'span[aria-label*="avis"]',
            'button[jsaction*="reviews"]',
            'div.F7nice button[jsaction*="reviews"]',
            'div.F7nice span[aria-label*="avis"]',
            'div.F7nice span[aria-label*="reviews"]',
        ]
        for selector in review_selectors:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            aria = await locator.get_attribute("aria-label")
            if aria:
                return aria.strip()
            text = (await locator.inner_text()).strip()
            if text:
                return text
        return None

    def _strip_field_prefix(self, value: str) -> str:
        lowered = value.lower()
        prefixes = (
            "adresse:",
            "address:",
            "téléphone:",
            "telephone:",
            "phone:",
            "numéro de téléphone:",
            "numero de telephone:",
        )
        for prefix in prefixes:
            if lowered.startswith(prefix):
                return value[len(prefix) :].strip()
        return value

    async def _website_from_page(self, page: Page) -> str | None:
        retries = self.settings.scraper_website_extract_retries
        for attempt in range(retries):
            website = await self._try_extract_website(page)
            if website:
                return website

            if attempt < retries - 1:
                await self._scroll_place_details_panel(page)
                await page.wait_for_timeout(self.settings.scraper_website_retry_delay_ms)

        return None

    async def _try_extract_website(self, page: Page) -> str | None:
        panel = page.locator(PLACE_PANEL_SELECTOR)

        for selector in WEBSITE_LINK_SELECTORS:
            locator = panel.locator(selector)
            count = await locator.count()
            for index in range(count):
                element = locator.nth(index)
                website = await self._website_from_element(element)
                if website:
                    return website

        links = panel.locator('a[href^="http"], a[href^="//"]')
        count = await links.count()
        for index in range(count):
            website = await self._website_from_element(links.nth(index))
            if website:
                return website

        return None

    async def _website_from_element(self, element: Locator) -> str | None:
        for attribute in ("href", "data-href", "data-url"):
            value = await element.get_attribute(attribute)
            website = parse_website_href(value)
            if website:
                return website

        aria = await element.get_attribute("aria-label")
        if aria:
            website = self._website_from_label(aria)
            if website:
                return website

        text = (await element.inner_text()).strip()
        if text:
            return self._website_from_label(text)

        return None

    def _website_from_label(self, value: str) -> str | None:
        lowered = value.lower()
        prefixes = (
            "site web:",
            "website:",
            "site internet:",
            "url:",
            "http://",
            "https://",
        )
        for prefix in prefixes:
            if lowered.startswith(prefix):
                candidate = value[len(prefix) :].strip()
                return parse_website_href(candidate)

        if "http://" in value or "https://" in value:
            for token in value.split():
                website = parse_website_href(token.strip(".,;"))
                if website:
                    return website

        if "." in value and " " not in value and not value.startswith("+"):
            return parse_website_href(value)

        return None

    async def extract_testimonials(
        self,
        page: Page,
        *,
        expected_business_name: str | None = None,
    ) -> list[Testimonial]:
        await self._wait_for_place_title(page)
        if expected_business_name and not await self._place_matches_name(page, expected_business_name):
            actual = await self._first_text(page, ["h1.DUwDvf", "h1"]) or ""
            logger.warning(
                "Skipping reviews — place title %r does not match expected %r",
                actual,
                expected_business_name,
            )
            return []

        await self._open_reviews_panel(page)
        await self._scroll_reviews_panel(page)

        main_panel = page.locator(PLACE_PANEL_SELECTOR)
        review_items = main_panel.locator("div[data-review-id]")
        try:
            await review_items.first.wait_for(state="attached", timeout=8000)
        except Exception:
            logger.warning("No review items found for %s", expected_business_name or page.url)
            return []

        count = min(
            await review_items.count(),
            self.settings.scraper_max_testimonials_per_business,
        )
        testimonials: list[Testimonial] = []
        seen_texts: set[str] = set()

        for index in range(count):
            try:
                item = review_items.nth(index)
                testimonial = await self._parse_review_item(item)
                if testimonial is None:
                    continue
                key = testimonial.text.strip().lower()
                if not key or key in seen_texts:
                    continue
                seen_texts.add(key)
                testimonials.append(testimonial)
            except Exception as exc:
                logger.debug("Failed to parse review %s: %s", index, exc)

        return testimonials

    async def _open_reviews_panel(self, page: Page) -> None:
        main_panel = page.locator(PLACE_PANEL_SELECTOR)
        tab_selectors = [
            'button[role="tab"][aria-label*="Avis"]',
            'button[role="tab"][aria-label*="Reviews"]',
            'button[aria-label*="avis"][aria-label*="Google"]',
            'button[aria-label*="reviews"][aria-label*="Google"]',
            'button[aria-label*="Avis"]',
            'button[aria-label*="Reviews"]',
            'button[jsaction*="reviews"]',
        ]
        for selector in tab_selectors:
            button = main_panel.locator(selector).first
            if await button.count() == 0:
                continue
            await button.click()
            await page.wait_for_timeout(1500)
            return

    async def _scroll_reviews_panel(self, page: Page) -> None:
        main_panel = page.locator(PLACE_PANEL_SELECTOR)
        panel_selectors = [
            'div.m6QErb.DxyBCb',
            'div.m6QErb',
            'div.section-scrollbox',
        ]
        for selector in panel_selectors:
            panel = main_panel.locator(selector).last
            if await panel.count() == 0:
                continue
            for _ in range(self.settings.scraper_testimonial_scroll_rounds):
                await panel.evaluate("element => { element.scrollTop = element.scrollHeight; }")
                await page.wait_for_timeout(700)
            return

    async def _wait_for_place_title(self, page: Page) -> None:
        try:
            await page.locator("h1.DUwDvf, h1").first.wait_for(state="visible", timeout=8000)
        except Exception:
            pass

    async def _place_matches_name(self, page: Page, expected_name: str) -> bool:
        actual = await self._first_text(page, ["h1.DUwDvf", "h1"])
        if not actual:
            return False
        return business_names_match(expected_name, actual)

    async def _parse_review_item(self, item: Locator) -> Testimonial | None:
        text = await self._first_locator_text(
            item,
            ["span.wiI7pd", "div.MyEned span", 'span[data-expandable-section]'],
        )
        if not text:
            return None

        author = await self._first_locator_text(item, ["div.d4r55", ".WNxzHc .d4r55"])
        date = await self._first_locator_text(item, ["span.rsqaWe", ".WNxzHc .rsqaWe"])

        rating = None
        rating_locator = item.locator(
            'span[role="img"][aria-label*="star"], span[role="img"][aria-label*="étoile"]'
        )
        if await rating_locator.count() > 0:
            aria = await rating_locator.first.get_attribute("aria-label")
            rating = parse_rating_from_aria(aria)

        return Testimonial(
            author=author,
            rating=rating,
            text=text.strip(),
            date=date,
        )

    async def _first_locator_text(self, root: Locator, selectors: list[str]) -> str | None:
        for selector in selectors:
            locator = root.locator(selector).first
            if await locator.count() == 0:
                continue
            text = (await locator.inner_text()).strip()
            if text:
                return text
        return None
