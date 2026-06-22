from decimal import Decimal

from app.models.enums import WebsiteReason
from app.scraper.website_detector import DetectionResult
from app.services.normalization_service import NormalizedBusiness
from app.services.prospect_record_service import build_prospect_from_scrape
from app.utils.url import normalize_maps_url


def _sample_business(**overrides: object) -> NormalizedBusiness:
    defaults = {
        "business_name": "Acme Plumber",
        "category": "Plumber",
        "address": "1 Rue de Paris, Lyon",
        "phone": "+33 4 00 00 00 00",
        "website": None,
        "rating": Decimal("4.5"),
        "review_count": 12,
        "maps_url": "https://maps.google.com/?cid=123",
    }
    defaults.update(overrides)
    return NormalizedBusiness(**defaults)  # type: ignore[arg-type]


def test_build_prospect_without_website_stores_full_details() -> None:
    business = _sample_business()
    detection = DetectionResult(has_website=False, reason=WebsiteReason.NO_URL)

    prospect = build_prospect_from_scrape(
        search_id=1,
        business=business,
        detection=detection,
    )

    assert prospect.has_website is False
    assert prospect.business_name == "Acme Plumber"
    assert prospect.category == "Plumber"
    assert prospect.address == "1 Rue de Paris, Lyon"
    assert prospect.phone == "+33 4 00 00 00 00"
    assert prospect.rating == Decimal("4.5")
    assert prospect.review_count == 12
    assert prospect.maps_url == normalize_maps_url(business.maps_url)
    assert prospect.website_reason == WebsiteReason.NO_URL


def test_build_prospect_with_website_stores_minimal_record_for_dedupe() -> None:
    business = _sample_business(website="https://example.com")
    detection = DetectionResult(has_website=True, reason=WebsiteReason.VALID)

    prospect = build_prospect_from_scrape(
        search_id=1,
        business=business,
        detection=detection,
    )

    assert prospect.has_website is True
    assert prospect.business_name == "Acme Plumber"
    assert prospect.website_reason == WebsiteReason.VALID
    assert prospect.maps_url == normalize_maps_url(business.maps_url)
    assert prospect.category is None
    assert prospect.address is None
    assert prospect.phone is None
    assert prospect.website is None
    assert prospect.rating is None
    assert prospect.review_count is None
