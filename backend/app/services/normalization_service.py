from dataclasses import dataclass
from decimal import Decimal

from app.scraper.business_parser import RawBusiness
from app.utils.address import normalize_address
from app.utils.phone import normalize_phone
from app.utils.prospect_identity import build_prospect_dedupe_key
from app.utils.url import normalize_maps_url, parse_website_href, resolve_maps_navigation_url


@dataclass
class NormalizedBusiness:
    business_name: str
    category: str | None
    address: str | None
    phone: str | None
    website: str | None
    rating: Decimal | None
    review_count: int | None
    maps_url: str | None


class NormalizationService:
    def normalize_batch(
        self,
        businesses: list[RawBusiness],
        country: str,
    ) -> list[NormalizedBusiness]:
        normalized: list[NormalizedBusiness] = []
        seen_keys: set[str] = set()

        for business in businesses:
            name = business.business_name.strip()
            if not name:
                continue

            address = normalize_address(business.address)
            phone = normalize_phone(business.phone, country)
            maps_source_url = business.maps_url
            maps_url = resolve_maps_navigation_url(
                maps_url=maps_source_url,
                business_name=name,
                address=address,
                city=None,
                country=country,
            ) or normalize_maps_url(maps_source_url)
            key, _ = build_prospect_dedupe_key(
                business_name=name,
                address=address,
                phone=phone,
                maps_url=maps_url,
                country=country,
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)

            normalized.append(
                NormalizedBusiness(
                    business_name=name,
                    category=(business.category or "").strip() or None,
                    address=address,
                    phone=phone,
                    website=parse_website_href(business.website),
                    rating=business.rating,
                    review_count=business.review_count,
                    maps_url=maps_url,
                )
            )

        return normalized
