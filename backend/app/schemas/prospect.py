from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import WebsiteReason


class TestimonialRead(BaseModel):
    author: str | None = None
    rating: float | None = None
    text: str
    date: str | None = None


class ProspectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    search_id: int
    business_name: str
    category: str | None
    address: str | None
    phone: str | None
    website: str | None
    rating: Decimal | None
    review_count: int | None
    maps_url: str | None
    has_website: bool
    website_reason: WebsiteReason
    testimonials: list[TestimonialRead] = Field(default_factory=list)
    created_at: datetime
    city: str | None = None
    country: str | None = None


class ProspectFilters(BaseModel):
    city: str | None = None
    category: str | None = None
    has_website: bool | None = None
    website_reason: WebsiteReason | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("city", "category", mode="before")
    @classmethod
    def strip_empty(cls, value: str | None) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped if stripped else None


class ProspectStats(BaseModel):
    total: int
    with_website: int
    without_website: int
