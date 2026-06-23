from unittest.mock import AsyncMock, MagicMock
import asyncio

import pytest

from app.core.config import Settings
from app.scraper.exceptions import GoogleMapsBlockedError
from app.scraper.maps_ui import assert_maps_page_accessible, detect_google_block, is_single_place_url
from app.scraper.rate_limit import bulk_failure_cooldown_seconds


def test_is_single_place_url() -> None:
    assert is_single_place_url("https://www.google.com/maps/place/Cafe+Paris")
    assert not is_single_place_url("https://www.google.com/maps/search/plombier+marseille")


def test_detect_google_block_on_sorry_url() -> None:
    page = MagicMock()
    page.url = "https://www.google.com/sorry/index"
    page.locator.return_value.count = AsyncMock(return_value=0)
    page.locator.return_value.inner_text = AsyncMock(return_value="")

    assert asyncio.run(detect_google_block(page)) == "sorry_page"


def test_detect_google_block_on_recaptcha() -> None:
    page = MagicMock()
    page.url = "https://www.google.com/maps"
    locator = MagicMock()
    locator.count = AsyncMock(side_effect=[1])
    page.locator.return_value = locator
    page.locator.return_value.inner_text = AsyncMock(return_value="")

    assert asyncio.run(detect_google_block(page)) == "captcha_challenge"


def test_detect_google_block_on_unusual_traffic_text() -> None:
    page = MagicMock()
    page.url = "https://www.google.com/maps"
    locator = MagicMock()
    locator.count = AsyncMock(return_value=0)
    page.locator.return_value = locator
    page.locator.return_value.inner_text = AsyncMock(
        return_value="Our systems have detected unusual traffic from your network."
    )

    assert asyncio.run(detect_google_block(page)) == "block_text:unusual traffic"


def test_assert_maps_page_accessible_raises() -> None:
    page = MagicMock()
    page.url = "https://www.google.com/sorry/index"
    page.locator.return_value.count = AsyncMock(return_value=0)
    page.locator.return_value.inner_text = AsyncMock(return_value="")

    with pytest.raises(GoogleMapsBlockedError):
        asyncio.run(assert_maps_page_accessible(page))


def test_bulk_failure_cooldown_exponential_with_cap() -> None:
    settings = Settings(
        bulk_failure_cooldown_seconds=30.0,
        bulk_failure_cooldown_max_seconds=120.0,
    )

    assert bulk_failure_cooldown_seconds(settings, 0) == 0.0
    assert bulk_failure_cooldown_seconds(settings, 1) == 30.0
    assert bulk_failure_cooldown_seconds(settings, 2) == 60.0
    assert bulk_failure_cooldown_seconds(settings, 5) == 120.0
