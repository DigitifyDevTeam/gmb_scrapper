from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import SearchStatus, enum_member_values


class BulkJob(Base):
    __tablename__ = "bulk_jobs"

    job_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_queries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_queries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prospects_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prospects_saved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prospects_saved_with_website: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prospects_saved_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prospects_skipped_duplicates: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    current_city: Mapped[str | None] = mapped_column(String(150), nullable=True)
    current_category: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[SearchStatus] = mapped_column(
        Enum(
            SearchStatus,
            name="search_status",
            native_enum=False,
            values_callable=enum_member_values,
        ),
        nullable=False,
        default=SearchStatus.PENDING,
    )
    pause_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stop_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cities: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    categories: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    max_queries: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
