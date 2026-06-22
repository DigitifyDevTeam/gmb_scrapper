import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass
class RawBusiness:
    business_name: str
    category: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    rating: Decimal | None = None
    review_count: int | None = None
    maps_url: str | None = None


class BusinessParser:
    def parse_listing_card(self, card_data: dict[str, Any]) -> RawBusiness | None:
        name = (card_data.get("business_name") or "").strip()
        if not name:
            return None

        return RawBusiness(
            business_name=name,
            category=self._clean_text(card_data.get("category")),
            address=self._clean_text(card_data.get("address")),
            phone=self._clean_text(card_data.get("phone")),
            website=self._clean_text(card_data.get("website")),
            rating=self._parse_rating(card_data.get("rating")),
            review_count=self._parse_review_count(card_data.get("review_count")),
            maps_url=self._clean_text(card_data.get("maps_url")),
        )

    def dedupe_key(self, business: RawBusiness) -> str:
        maps_url = (business.maps_url or "").strip().lower()
        if maps_url:
            return f"url:{maps_url}"
        name = business.business_name.strip().lower()
        address = (business.address or "").strip().lower()
        return f"name:{name}|addr:{address}"

    def _clean_text(self, value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    def _parse_rating(self, value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            text = str(value).strip()
            decimal_match = re.search(r"(\d+[.,]\d+)", text)
            if decimal_match:
                return Decimal(decimal_match.group(1).replace(",", "."))
            integer_match = re.search(r"(\d+)", text)
            if not integer_match:
                return None
            return Decimal(integer_match.group(1))
        except (InvalidOperation, ValueError):
            return None

    def _parse_review_count(self, value: Any) -> int | None:
        if value is None:
            return None
        normalized = (
            str(value)
            .replace("\xa0", "")
            .replace("\u202f", "")
            .replace(" ", "")
        )
        digits = re.sub(r"[^\d]", "", normalized)
        if not digits:
            return None
        return int(digits)
