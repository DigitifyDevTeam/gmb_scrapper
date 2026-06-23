import re
import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TestimonialFetchTarget:
    """Identifies a Maps place when fetching reviews in a second navigation pass."""

    place_key: str
    navigation_url: str
    business_name: str


@dataclass
class Testimonial:
    text: str
    author: str | None = None
    rating: float | None = None
    date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "author": self.author,
            "rating": self.rating,
            "text": self.text,
            "date": self.date,
        }


def parse_rating_from_aria(aria_label: str | None) -> float | None:
    if not aria_label:
        return None
    match = re.search(r"(\d+[.,]?\d*)", aria_label)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def normalize_name_for_match(name: str) -> str:
    text = unicodedata.normalize("NFKD", name.lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def business_names_match(expected: str, actual: str) -> bool:
    left = normalize_name_for_match(expected)
    right = normalize_name_for_match(actual)
    if not left or not right:
        return False
    if left == right:
        return True
    if left in right or right in left:
        return True
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
    return overlap >= 0.75


def build_testimonial_place_key(
    *,
    maps_place_id: str | None = None,
    maps_url: str | None = None,
) -> str | None:
    if maps_place_id:
        return f"place:{maps_place_id.lower()}"
    if maps_url:
        cleaned = maps_url.strip().lower()
        if cleaned:
            return f"url:{cleaned}"
    return None
