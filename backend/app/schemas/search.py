from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SearchStatus


class SearchCreate(BaseModel):
    country: str = Field(..., min_length=1, max_length=100)
    city: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=150)


class SearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    country: str
    city: str
    category: str
    status: SearchStatus
    created_at: datetime


class SearchListResponse(BaseModel):
    items: list[SearchRead]
    total: int
