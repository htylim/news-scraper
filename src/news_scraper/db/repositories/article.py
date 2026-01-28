"""Article repository for database operations."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from news_scraper.db.models import Article, Source
from news_scraper.logging import get_logger
from news_scraper.parsers import ParsedArticle


class ArticleRepository:
    """Repository for Article persistence operations.

    Handles upsert logic with deduplication rules:
    - Same URL from same source: update all fields
    - Same URL from different source: skip with warning
    """

    def __init__(self, session: Session) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy session for database operations.
        """
        self._session = session
        self._log = get_logger()

    def upsert_from_parsed(
        self,
        parsed: ParsedArticle,
        source: Source,
        seen_at: datetime | None = None,
    ) -> Article | None:
        """Create or update article from parsed data.

        Args:
            parsed: Parsed article data from scraper.
            source: Source the article was scraped from.
            seen_at: Timestamp for last_seen_at (defaults to now).

        Returns:
            Article instance if created/updated, None if skipped.
        """
        seen_at = seen_at or datetime.now()

        # Check if URL already exists
        existing = self._find_by_url(parsed.url)

        if existing:
            if existing.source_id != source.id:
                # URL exists from different source - skip
                self._log.warning(
                    "Article URL already exists from different source",
                    url=parsed.url,
                    existing_source_id=existing.source_id,
                    new_source_id=source.id,
                )
                return None

            # Same source - update existing article
            return self._update_article(existing, parsed, seen_at)

        # New article - create
        return self._create_article(parsed, source, seen_at)

    def _find_by_url(self, url: str) -> Article | None:
        """Find article by URL.

        Args:
            url: Article URL to search for.

        Returns:
            Article if found, None otherwise.
        """
        stmt = select(Article).where(Article.url == url)
        return self._session.scalars(stmt).first()

    def _create_article(
        self,
        parsed: ParsedArticle,
        source: Source,
        seen_at: datetime,
    ) -> Article:
        """Create new article from parsed data.

        Args:
            parsed: Parsed article data.
            source: Source the article belongs to.
            seen_at: Timestamp for last_seen_at.

        Returns:
            Newly created Article instance.
        """
        article = Article(
            headline=parsed.headline,
            description=parsed.summary,
            url=parsed.url,
            image_url=parsed.image_url,
            position=parsed.position,
            source_id=source.id,
            last_seen_at=seen_at,
        )
        self._session.add(article)
        self._log.debug("Created new article", url=parsed.url, position=parsed.position)
        return article

    def _update_article(
        self,
        article: Article,
        parsed: ParsedArticle,
        seen_at: datetime,
    ) -> Article:
        """Update existing article with new data.

        Args:
            article: Existing article to update.
            parsed: New parsed data.
            seen_at: Timestamp for last_seen_at.

        Returns:
            Updated Article instance.
        """
        article.headline = parsed.headline
        article.description = parsed.summary
        article.image_url = parsed.image_url
        article.position = parsed.position
        article.last_seen_at = seen_at
        self._log.debug(
            "Updated existing article", url=parsed.url, position=parsed.position
        )
        return article

    def bulk_upsert_from_parsed(
        self,
        parsed_articles: list[ParsedArticle],
        source: Source,
        seen_at: datetime | None = None,
    ) -> tuple[int, int, int]:
        """Bulk upsert articles from parsed data.

        Args:
            parsed_articles: List of parsed articles.
            source: Source the articles were scraped from.
            seen_at: Timestamp for last_seen_at (defaults to now).

        Returns:
            Tuple of (created_count, updated_count, skipped_count).
        """
        seen_at = seen_at or datetime.now()
        created = 0
        updated = 0
        skipped = 0

        # Pre-dedupe by URL (first occurrence wins)
        seen_urls: set[str] = set()
        unique_parsed: list[ParsedArticle] = []
        for parsed in parsed_articles:
            if parsed.url in seen_urls:
                self._log.debug(
                    "Skipping duplicate URL in batch",
                    url=parsed.url,
                    position=parsed.position,
                )
                skipped += 1
                continue
            seen_urls.add(parsed.url)
            unique_parsed.append(parsed)

        if not unique_parsed:
            return created, updated, skipped

        # Prefetch all existing articles in one query
        urls = [p.url for p in unique_parsed]
        stmt = select(Article).where(Article.url.in_(urls))
        existing_articles = self._session.scalars(stmt).all()
        existing_by_url = {article.url: article for article in existing_articles}

        for parsed in unique_parsed:
            existing = existing_by_url.get(parsed.url)

            if existing:
                if existing.source_id != source.id:
                    self._log.warning(
                        "Article URL already exists from different source",
                        url=parsed.url,
                        existing_source_id=existing.source_id,
                        new_source_id=source.id,
                    )
                    skipped += 1
                    continue

                self._update_article(existing, parsed, seen_at)
                updated += 1
            else:
                self._create_article(parsed, source, seen_at)
                created += 1

        return created, updated, skipped
