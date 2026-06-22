import asyncio
import logging
import random

from playwright.async_api import Locator, Page

from app.core.config import get_settings
from app.scraper.business_parser import BusinessParser, RawBusiness
from app.scraper.testimonial import Testimonial, parse_rating_from_aria
from app.utils.phone import extract_phone_from_data_item_id

logger = logging.getLogger(__name__)


class ExtractionEngine:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.parser = BusinessParser()

    async def extract_businesses(self, page: Page, max_results: int) -> list[RawBusiness]:
        card_locator = page.locator('div[role="feed"] a[href*="/maps/place"]')
        count = min(await card_locator.count(), max_results)
        businesses: list[RawBusiness] = []
        seen_keys: set[str] = set()

        for index in range(count):
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

            await asyncio.sleep(
                (self.settings.scraper_request_delay_ms + random.randint(0, 300)) / 1000
            )

        return businesses

    async def _extract_card(self, page: Page, card: Locator) -> RawBusiness | None:
        await card.scroll_into_view_if_needed()
        await card.click()
        await self._wait_for_place_details(page)

        maps_url = page.url if "/maps/place" in page.url else None
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
        detail_selectors = (
            'h1.DUwDvf',
            'button[data-item-id="address"]',
            'button[data-item-id^="phone:tel:"]',
            'button[data-item-id="phone"]',
        )
        for selector in detail_selectors:
            try:
                await page.wait_for_selector(selector, timeout=2500)
                return
            except Exception:
                continue
        await page.wait_for_timeout(1200)

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
        website_button = page.locator('a[data-item-id="authority"]')
        if await website_button.count() > 0:
            href = await website_button.first.get_attribute("href")
            if href:
                return href.strip()

        links = page.locator('a[href^="http"]')
        count = await links.count()
        for idx in range(count):
            href = await links.nth(idx).get_attribute("href")
            if href and "google.com" not in href and "goo.gl" not in href:
                return href.strip()

        return None

    async def extract_testimonials(self, page: Page) -> list[Testimonial]:
        await self._open_reviews_panel(page)
        await self._scroll_reviews_panel(page)

        review_items = page.locator("div[data-review-id]")
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
            button = page.locator(selector).first
            if await button.count() > 0:
                await button.click()
                await page.wait_for_timeout(1500)
                return

    async def _scroll_reviews_panel(self, page: Page) -> None:
        panel_selectors = [
            'div[role="main"] div.m6QErb.DxyBCb',
            'div[role="main"] div.m6QErb',
            'div.section-scrollbox',
        ]
        for selector in panel_selectors:
            panel = page.locator(selector).last
            if await panel.count() == 0:
                continue
            for _ in range(self.settings.scraper_testimonial_scroll_rounds):
                await panel.evaluate("element => { element.scrollTop = element.scrollHeight; }")
                await page.wait_for_timeout(700)
            return

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
