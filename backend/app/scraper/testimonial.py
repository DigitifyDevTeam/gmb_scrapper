import re
from dataclasses import dataclass
from typing import Any


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
