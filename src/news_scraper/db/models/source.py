"""Source model for news sources."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from news_scraper.db.base import Base, TimestampMixin
from news_scraper.validation import ValidationError, validate_slug

if TYPE_CHECKING:
    from news_scraper.db.models.article import Article


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

    # Relationships
    articles: Mapped[list["Article"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )

    @validates("name")
    def validate_name(self, _key: str, value: str) -> str:
        """Validate and normalize name as a slug.

        Args:
            _key: The attribute name (always "name").
            value: The value being set.

        Returns:
            The normalized lowercase slug.

        Raises:
            ValueError: If the name is not a valid slug.
        """
        try:
            return validate_slug(value, field_name="name")
        except ValidationError as e:
            raise ValueError(str(e)) from e

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, name={self.name!r})>"
