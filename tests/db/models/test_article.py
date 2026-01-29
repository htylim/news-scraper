"""Tests for Article model."""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from news_scraper.db.models import Article, Source


class TestArticleModel:
    """Tests for the Article model."""

    @pytest.fixture
    def source(self, db_session: Session) -> Source:
        """Create a source for article tests."""
        source = Source(name="testsource", url="https://test.com")
        db_session.add(source)
        db_session.commit()
        return source

    def test_create_article_required_fields(
        self, db_session: Session, source: Source
    ) -> None:
        """Article can be created with required fields."""
        article = Article(
            headline="Test Headline",
            url="https://test.com/article",
            position=1,
            source_id=source.id,
        )
        db_session.add(article)
        db_session.commit()

        assert article.id is not None
        assert article.headline == "Test Headline"
        assert article.url == "https://test.com/article"
        assert article.position == 1
        assert article.source_id == source.id
        assert article.description is None
        assert article.image_url is None

    def test_create_article_all_fields(
        self, db_session: Session, source: Source
    ) -> None:
        """Article can be created with all fields."""
        article = Article(
            headline="Full Article",
            description="Article description",
            url="https://test.com/full-article",
            image_url="https://test.com/image.jpg",
            position=5,
            source_id=source.id,
            last_seen_at=datetime(2026, 1, 26, 12, 0, 0),
        )
        db_session.add(article)
        db_session.commit()

        assert article.description == "Article description"
        assert article.image_url == "https://test.com/image.jpg"
        assert article.position == 5

    def test_timestamps_set_on_create(
        self, db_session: Session, source: Source
    ) -> None:
        """created_at and updated_at are set on insert."""
        article = Article(
            headline="Time Test",
            url="https://test.com/time",
            position=1,
            source_id=source.id,
        )
        db_session.add(article)
        db_session.commit()

        assert article.created_at is not None
        assert article.updated_at is not None
        assert article.last_seen_at is not None

    def test_url_unique_constraint(self, db_session: Session, source: Source) -> None:
        """Duplicate URLs are rejected."""
        article1 = Article(
            headline="First",
            url="https://test.com/same-url",
            position=1,
            source_id=source.id,
        )
        db_session.add(article1)
        db_session.commit()

        article2 = Article(
            headline="Second",
            url="https://test.com/same-url",
            position=2,
            source_id=source.id,
        )
        db_session.add(article2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_source_relationship(self, db_session: Session, source: Source) -> None:
        """Article has relationship to source."""
        article = Article(
            headline="Relationship Test",
            url="https://test.com/rel",
            position=1,
            source_id=source.id,
        )
        db_session.add(article)
        db_session.commit()

        assert article.source == source
        assert article in source.articles

    def test_repr(self, db_session: Session, source: Source) -> None:
        """__repr__ returns readable string."""
        article = Article(
            headline="Repr Test Article with Long Headline",
            url="https://test.com/repr",
            position=1,
            source_id=source.id,
        )
        db_session.add(article)
        db_session.commit()

        result = repr(article)
        assert "Article" in result
        assert str(article.id) in result

    def test_source_id_required(self, db_session: Session) -> None:
        """source_id is required (NOT NULL)."""
        article = Article(
            headline="No Source",
            url="https://test.com/no-source",
            position=1,
        )
        db_session.add(article)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_headline_required(self, db_session: Session, source: Source) -> None:
        """headline is required (NOT NULL)."""
        article = Article(
            url="https://test.com/no-headline",
            position=1,
            source_id=source.id,
        )
        db_session.add(article)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_url_required(self, db_session: Session, source: Source) -> None:
        """url is required (NOT NULL)."""
        article = Article(
            headline="No URL",
            position=1,
            source_id=source.id,
        )
        db_session.add(article)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_position_required(self, db_session: Session, source: Source) -> None:
        """position is required (NOT NULL)."""
        article = Article(
            headline="No Position",
            url="https://test.com/no-position",
            source_id=source.id,
        )
        db_session.add(article)
        with pytest.raises(IntegrityError):
            db_session.commit()
