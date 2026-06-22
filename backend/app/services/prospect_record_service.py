from app.models.prospect import Prospect
from app.scraper.website_detector import DetectionResult
from app.services.normalization_service import NormalizedBusiness
from app.utils.url import normalize_maps_url


def build_prospect_from_scrape(
    *,
    search_id: int,
    business: NormalizedBusiness,
    detection: DetectionResult,
    testimonials: list[dict] | None = None,
) -> Prospect:
    """Full GMB details for leads; name + dedupe key only when they have a website."""
    maps_url = normalize_maps_url(business.maps_url)

    if detection.has_website:
        return Prospect(
            search_id=search_id,
            business_name=business.business_name,
            has_website=True,
            website_reason=detection.reason,
            maps_url=maps_url,
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
        has_website=False,
        website_reason=detection.reason,
        testimonials=testimonials or None,
    )
