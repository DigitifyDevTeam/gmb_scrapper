from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import SearchStatus, enum_member_values


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[SearchStatus] = mapped_column(
        Enum(
            SearchStatus,
            name="search_status",
            native_enum=False,
            values_callable=enum_member_values,
        ),
        default=SearchStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    prospects: Mapped[list["Prospect"]] = relationship(
        "Prospect",
        back_populates="search",
        cascade="all, delete-orphan",
    )


from app.models.prospect import Prospect  # noqa: E402
