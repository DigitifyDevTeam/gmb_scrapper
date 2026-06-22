from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import WebsiteReason


class Prospect(Base):
    __tablename__ = "prospects"
    __table_args__ = (
        Index(
            "ix_prospects_search_name_address",
            "search_id",
            "business_name",
            "address",
            mysql_length={"address": 191},
        ),
        Index("ix_prospects_category", "category"),
        Index("ix_prospects_has_website", "has_website"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("searches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(150), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(2, 1), nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maps_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_website: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    website_reason: Mapped[WebsiteReason] = mapped_column(
        Enum(WebsiteReason, name="website_reason", native_enum=False),
        default=WebsiteReason.NO_URL,
        nullable=False,
    )
    testimonials: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    search: Mapped["Search"] = relationship("Search", back_populates="prospects")


from app.models.search import Search  # noqa: E402
