"""Source model for news sources."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from news_scraper.db.base import Base, TimestampMixin


class Source(TimestampMixin, Base):
    """News source configuration."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, name={self.name!r})>"
