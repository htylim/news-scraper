"""Article model for scraped news articles."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from news_scraper.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from news_scraper.db.models.source import Source


class Article(TimestampMixin, Base):
    """Scraped news article from a source's front page.

    Attributes:
        id: Auto-increment primary key.
        headline: Article title.
        description: Brief summary/subheadline (optional).
        url: Full URL to article (unique, indexed for fast lookups).
        image_url: URL of associated image (optional).
        position: Position on portal (1 = top/most prominent).
        source_id: Foreign key to source this article was scraped from.
        last_seen_at: When article was last seen in a scrape.
        created_at: When article was first scraped.
        updated_at: When article record was last modified.
    """

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    headline: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    position: Mapped[int] = mapped_column(nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # Relationships
    source: Mapped["Source"] = relationship(back_populates="articles")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_articles_url", "url"),
        Index("ix_articles_source_id", "source_id"),
        Index("ix_articles_last_seen_at", "last_seen_at"),
    )

    def __repr__(self) -> str:
        return f"<Article(id={self.id}, headline={self.headline[:50]!r}...)>"
