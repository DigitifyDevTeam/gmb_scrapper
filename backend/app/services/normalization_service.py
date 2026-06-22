from dataclasses import dataclass
from decimal import Decimal

from app.scraper.business_parser import RawBusiness
from app.utils.address import normalize_address
from app.utils.phone import normalize_phone
from app.utils.url import normalize_maps_url


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
            key = self._dedupe_key(name, address, business.maps_url)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            normalized.append(
                NormalizedBusiness(
                    business_name=name,
                    category=(business.category or "").strip() or None,
                    address=address,
                    phone=phone,
                    website=(business.website or "").strip() or None,
                    rating=business.rating,
                    review_count=business.review_count,
                    maps_url=normalize_maps_url(business.maps_url),
                )
            )

        return normalized

    def _dedupe_key(self, name: str, address: str | None, maps_url: str | None) -> str:
        normalized_url = normalize_maps_url(maps_url)
        if normalized_url:
            return f"url:{normalized_url.lower()}"
        return f"name:{name.lower()}|addr:{(address or '').lower()}"
