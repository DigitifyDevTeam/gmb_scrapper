from pydantic import BaseModel, Field

from app.models.enums import SearchStatus


class ScrapingStartRequest(BaseModel):
    search_id: int = Field(..., gt=0)


class ScrapingStartResponse(BaseModel):
    job_id: str
    search_id: int
    status: SearchStatus


class ScrapingStatusResponse(BaseModel):
    job_id: str
    search_id: int
    status: SearchStatus
    prospects_found: int = 0
    prospects_saved: int = 0
    error: str | None = None


class BulkScrapingStartRequest(BaseModel):
    country: str = Field(default="France", min_length=1, max_length=100)
    target_count: int | None = Field(default=None, gt=0, le=100_000)
    cities: list[str] | None = None
    categories: list[str] | None = None
    max_queries: int | None = Field(default=None, gt=0, le=10_000)


class BulkScrapingStartResponse(BaseModel):
    job_id: str
    country: str
    target_count: int
    total_queries: int
    status: SearchStatus


class BulkScrapingStatusResponse(BaseModel):
    job_id: str
    country: str
    target_count: int
    total_queries: int
    completed_queries: int
    prospects_found: int
    prospects_saved: int
    prospects_saved_with_website: int = 0
    prospects_saved_total: int = 0
    prospects_skipped_duplicates: int
    current_city: str | None = None
    current_category: str | None = None
    status: SearchStatus
    error: str | None = None
