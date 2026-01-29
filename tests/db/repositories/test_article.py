"""Tests for ArticleRepository."""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from news_scraper.db.models import Article, Source
from news_scraper.db.repositories import ArticleRepository
from news_scraper.parsers import ParsedArticle


class TestArticleRepository:
    """Tests for ArticleRepository."""

    @pytest.fixture
    def source(self, db_session: Session) -> Source:
        """Create a source for tests."""
        source = Source(name="testsource", url="https://test.com")
        db_session.add(source)
        db_session.commit()
        return source

    @pytest.fixture
    def other_source(self, db_session: Session) -> Source:
        """Create another source for cross-source tests."""
        source = Source(name="othersource", url="https://other.com")
        db_session.add(source)
        db_session.commit()
        return source

    @pytest.fixture
    def repo(self, db_session: Session) -> ArticleRepository:
        """Create repository instance."""
        return ArticleRepository(db_session)

    def test_upsert_creates_new_article(
        self, db_session: Session, repo: ArticleRepository, source: Source
    ) -> None:
        """upsert_from_parsed creates new article when URL doesn't exist."""
        parsed = ParsedArticle(
            headline="New Article",
            url="https://test.com/new",
            position=1,
            summary="Summary text",
            image_url="https://test.com/image.jpg",
        )

        result = repo.upsert_from_parsed(parsed, source)
        db_session.commit()

        assert result is not None
        assert result.headline == "New Article"
        assert result.url == "https://test.com/new"
        assert result.description == "Summary text"
        assert result.position == 1
        assert result.source_id == source.id

    def test_upsert_updates_existing_article(
        self, db_session: Session, repo: ArticleRepository, source: Source
    ) -> None:
        """upsert_from_parsed updates article when URL exists for same source."""
        # Create existing article
        existing = Article(
            headline="Old Headline",
            url="https://test.com/existing",
            position=5,
            source_id=source.id,
        )
        db_session.add(existing)
        db_session.commit()

        # Upsert with new data
        parsed = ParsedArticle(
            headline="New Headline",
            url="https://test.com/existing",
            position=1,
            summary="New summary",
        )

        result = repo.upsert_from_parsed(parsed, source)
        db_session.commit()

        assert result is not None
        assert result.id == existing.id
        assert result.headline == "New Headline"
        assert result.position == 1
        assert result.description == "New summary"

    def test_upsert_skips_cross_source_duplicate(
        self,
        db_session: Session,
        repo: ArticleRepository,
        source: Source,
        other_source: Source,
    ) -> None:
        """upsert_from_parsed skips URL that exists from different source."""
        # Create article from other source
        existing = Article(
            headline="Other Source Article",
            url="https://test.com/cross-source",
            position=1,
            source_id=other_source.id,
        )
        db_session.add(existing)
        db_session.commit()

        # Try to upsert same URL from different source
        parsed = ParsedArticle(
            headline="Same URL Different Source",
            url="https://test.com/cross-source",
            position=1,
        )

        result = repo.upsert_from_parsed(parsed, source)

        assert result is None
        # Existing article unchanged
        assert existing.headline == "Other Source Article"

    def test_upsert_updates_last_seen_at(
        self, db_session: Session, repo: ArticleRepository, source: Source
    ) -> None:
        """upsert_from_parsed updates last_seen_at timestamp."""
        # Create existing article with old timestamp
        existing = Article(
            headline="Test",
            url="https://test.com/timestamp",
            position=1,
            source_id=source.id,
            last_seen_at=datetime(2025, 1, 1, 0, 0, 0),
        )
        db_session.add(existing)
        db_session.commit()

        # Upsert with new timestamp
        new_time = datetime(2026, 1, 26, 12, 0, 0)
        parsed = ParsedArticle(
            headline="Test",
            url="https://test.com/timestamp",
            position=1,
        )

        repo.upsert_from_parsed(parsed, source, seen_at=new_time)
        db_session.commit()

        assert existing.last_seen_at == new_time

    def test_upsert_clears_optional_fields(
        self, db_session: Session, repo: ArticleRepository, source: Source
    ) -> None:
        """upsert_from_parsed clears optional fields when new data has None."""
        # Create existing article with optional fields populated
        existing = Article(
            headline="Original",
            url="https://test.com/clear-fields",
            position=1,
            source_id=source.id,
            description="Original summary",
            image_url="https://test.com/original.jpg",
        )
        db_session.add(existing)
        db_session.commit()

        # Upsert with None for optional fields
        parsed = ParsedArticle(
            headline="Updated",
            url="https://test.com/clear-fields",
            position=2,
            summary=None,
            image_url=None,
        )

        result = repo.upsert_from_parsed(parsed, source)
        db_session.commit()

        assert result is not None
        assert result.id == existing.id
        assert result.description is None
        assert result.image_url is None


class TestArticleRepositoryBulkUpsert:
    """Tests for bulk_upsert_from_parsed."""

    @pytest.fixture
    def source(self, db_session: Session) -> Source:
        """Create a source for tests."""
        source = Source(name="bulksource", url="https://bulk.com")
        db_session.add(source)
        db_session.commit()
        return source

    @pytest.fixture
    def other_source(self, db_session: Session) -> Source:
        """Create another source."""
        source = Source(name="otherbulk", url="https://otherbulk.com")
        db_session.add(source)
        db_session.commit()
        return source

    @pytest.fixture
    def repo(self, db_session: Session) -> ArticleRepository:
        """Create repository instance."""
        return ArticleRepository(db_session)

    def test_bulk_upsert_returns_counts(
        self, db_session: Session, repo: ArticleRepository, source: Source
    ) -> None:
        """bulk_upsert_from_parsed returns correct counts."""
        parsed = [
            ParsedArticle(headline="Article 1", url="https://bulk.com/1", position=1),
            ParsedArticle(headline="Article 2", url="https://bulk.com/2", position=2),
            ParsedArticle(headline="Article 3", url="https://bulk.com/3", position=3),
        ]

        created, updated, skipped = repo.bulk_upsert_from_parsed(parsed, source)
        db_session.commit()

        assert created == 3
        assert updated == 0
        assert skipped == 0

    def test_bulk_upsert_mixed_new_and_existing(
        self, db_session: Session, repo: ArticleRepository, source: Source
    ) -> None:
        """bulk_upsert_from_parsed handles mix of new and existing."""
        # Create existing article
        existing = Article(
            headline="Existing",
            url="https://bulk.com/existing",
            position=5,
            source_id=source.id,
        )
        db_session.add(existing)
        db_session.commit()

        parsed = [
            ParsedArticle(headline="New", url="https://bulk.com/new", position=1),
            ParsedArticle(
                headline="Updated Existing",
                url="https://bulk.com/existing",
                position=2,
            ),
        ]

        created, updated, skipped = repo.bulk_upsert_from_parsed(parsed, source)
        db_session.commit()

        assert created == 1
        assert updated == 1
        assert skipped == 0
        assert existing.headline == "Updated Existing"
        assert existing.position == 2

    def test_bulk_upsert_with_cross_source_duplicates(
        self,
        db_session: Session,
        repo: ArticleRepository,
        source: Source,
        other_source: Source,
    ) -> None:
        """bulk_upsert_from_parsed counts skipped cross-source duplicates."""
        # Create article from other source
        other_article = Article(
            headline="Other Source",
            url="https://bulk.com/cross",
            position=1,
            source_id=other_source.id,
        )
        db_session.add(other_article)
        db_session.commit()

        parsed = [
            ParsedArticle(headline="New", url="https://bulk.com/new", position=1),
            ParsedArticle(headline="Cross", url="https://bulk.com/cross", position=2),
        ]

        created, updated, skipped = repo.bulk_upsert_from_parsed(parsed, source)
        db_session.commit()

        assert created == 1
        assert updated == 0
        assert skipped == 1

    def test_bulk_upsert_dedupes_within_batch(
        self, db_session: Session, repo: ArticleRepository, source: Source
    ) -> None:
        """bulk_upsert keeps first occurrence when batch has duplicate URLs."""
        parsed = [
            ParsedArticle(
                headline="First Occurrence", url="https://bulk.com/dupe", position=1
            ),
            ParsedArticle(
                headline="New Article", url="https://bulk.com/new", position=2
            ),
            ParsedArticle(
                headline="Second Occurrence", url="https://bulk.com/dupe", position=3
            ),
        ]

        created, updated, skipped = repo.bulk_upsert_from_parsed(parsed, source)
        db_session.commit()

        assert created == 2
        assert updated == 0
        assert skipped == 1

        # Verify first occurrence was kept
        from sqlalchemy import select

        stmt = select(Article).where(Article.url == "https://bulk.com/dupe")
        article = db_session.scalars(stmt).first()
        assert article is not None
        assert article.headline == "First Occurrence"
        assert article.position == 1

    def test_bulk_upsert_empty_list(
        self,
        db_session: Session,  # noqa: ARG002
        repo: ArticleRepository,
        source: Source,
    ) -> None:
        """bulk_upsert_from_parsed handles empty list."""
        created, updated, skipped = repo.bulk_upsert_from_parsed([], source)
        assert created == 0
        assert updated == 0
        assert skipped == 0

    def test_bulk_upsert_all_duplicates_in_batch(
        self, db_session: Session, repo: ArticleRepository, source: Source
    ) -> None:
        """bulk_upsert_from_parsed handles batch where all items are duplicates."""
        parsed = [
            ParsedArticle(headline="First", url="https://bulk.com/same", position=1),
            ParsedArticle(headline="Second", url="https://bulk.com/same", position=2),
            ParsedArticle(headline="Third", url="https://bulk.com/same", position=3),
        ]

        created, updated, skipped = repo.bulk_upsert_from_parsed(parsed, source)
        db_session.commit()

        assert created == 1
        assert updated == 0
        assert skipped == 2

    def test_bulk_upsert_sets_seen_at_on_created(
        self, db_session: Session, repo: ArticleRepository, source: Source
    ) -> None:
        """bulk_upsert_from_parsed applies seen_at to newly created articles."""
        from sqlalchemy import select

        seen_at = datetime(2026, 1, 28, 10, 0, 0)
        parsed = [
            ParsedArticle(headline="New 1", url="https://bulk.com/new1", position=1),
            ParsedArticle(headline="New 2", url="https://bulk.com/new2", position=2),
        ]

        repo.bulk_upsert_from_parsed(parsed, source, seen_at=seen_at)
        db_session.commit()

        stmt = select(Article).where(Article.source_id == source.id)
        articles = db_session.scalars(stmt).all()

        assert len(articles) == 2
        for article in articles:
            assert article.last_seen_at == seen_at

    def test_bulk_upsert_sets_seen_at_on_updated(
        self, db_session: Session, repo: ArticleRepository, source: Source
    ) -> None:
        """bulk_upsert_from_parsed applies seen_at to updated articles."""
        old_time = datetime(2025, 1, 1, 0, 0, 0)
        existing = Article(
            headline="Existing",
            url="https://bulk.com/existing",
            position=5,
            source_id=source.id,
            last_seen_at=old_time,
        )
        db_session.add(existing)
        db_session.commit()

        new_time = datetime(2026, 1, 28, 12, 0, 0)
        parsed = [
            ParsedArticle(
                headline="Updated", url="https://bulk.com/existing", position=1
            ),
        ]

        repo.bulk_upsert_from_parsed(parsed, source, seen_at=new_time)
        db_session.commit()

        assert existing.last_seen_at == new_time
