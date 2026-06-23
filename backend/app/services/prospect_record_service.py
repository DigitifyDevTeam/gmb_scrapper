from app.models.prospect import Prospect
from app.scraper.website_detector import DetectionResult
from app.services.normalization_service import NormalizedBusiness
from app.utils.prospect_identity import build_google_maps_profile_url, build_prospect_dedupe_key
from app.utils.url import normalize_url, parse_website_href


def build_prospect_from_scrape(
    *,
    search_id: int,
    business: NormalizedBusiness,
    detection: DetectionResult,
    testimonials: list[dict] | None = None,
    country: str | None = None,
    city: str | None = None,
) -> Prospect:
    """Leads without a website get full GMB details; verified sites keep name + URL only."""
    dedupe_key, maps_place_id = build_prospect_dedupe_key(
        business_name=business.business_name,
        address=business.address,
        phone=business.phone,
        maps_url=business.maps_url,
        country=country,
    )
    maps_url = build_google_maps_profile_url(
        business_name=business.business_name,
        address=business.address,
        city=city,
        country=country,
        maps_place_id=maps_place_id,
        maps_url=business.maps_url,
    )

    if detection.has_website:
        website = parse_website_href(business.website) or normalize_url(business.website or "") or None
        return Prospect(
            search_id=search_id,
            business_name=business.business_name,
            website=website,
            has_website=True,
            website_reason=detection.reason,
            maps_place_id=maps_place_id,
            dedupe_key=dedupe_key,
        )

    return Prospect(
        search_id=search_id,
        business_name=business.business_name,
        category=business.category,
        address=business.address,
        phone=business.phone,
        website=business.website,
        rating=business.rating,
        review_count=business.review_count,
        maps_url=maps_url,
        maps_place_id=maps_place_id,
        dedupe_key=dedupe_key,
        has_website=False,
        website_reason=detection.reason,
        testimonials=testimonials or None,
    )
