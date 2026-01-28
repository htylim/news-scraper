# S006: Add Infobae Scraping - Part 3 (Article Persistence)

Persist scraped articles to the database with deduplication and position tracking.

## Goal

Extend the scraper to store parsed articles in the database:

```bash
news-scraper -s infobae
```

The command will:
1. Fetch rendered HTML (Part 1)
2. Parse HTML to extract articles (Part 2)
3. **NEW**: Persist articles to database with deduplication
4. Print summary of new/updated articles to console

Each article stores:
- **headline**: Article title
- **description**: Brief summary/subheadline (maps from `summary` in parsed data)
- **url**: Link to full article (unique constraint, indexed)
- **image_url**: Associated image URL
- **position**: Relative position on the portal (1 = top, higher = less prominent)
- **source_id**: Foreign key to Source (NOT NULL)
- **last_seen_at**: Timestamp of most recent scrape where article appeared
- **created_at**: Timestamp of first scrape (auto-set)
- **updated_at**: Timestamp of last modification (auto-updated)

## Architecture

### Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────┐
│   Browser   │────>│    Parser    │────>│   Persistence   │────>│    DB    │
│  (HTML)     │     │(ParsedArticle)│     │   (Article)     │     │ (SQLite) │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────┘
```

### Deduplication Rules

1. **Within same scrape**: Same URL appears multiple times → keep first occurrence only (lowest position number wins)
2. **Across scrapes (same source)**: URL already in DB → update all fields except URL, update `last_seen_at`
3. **Across sources**: URL already in DB from different source → log warning, skip (don't create duplicate)

### Position Semantics

- Position 1 = first/top article (most prominent)
- Position N = Nth article from top
- Position reflects importance: lower number = more important
- Position updated on each scrape (articles can move up/down)

## Deliverables

### 1. Rename Article Dataclass to ParsedArticle

**File:** `src/news_scraper/parsers/base.py`

Rename to clarify this is parser output, not DB model.

```python
"""Base classes for HTML parsers."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ParsedArticle:
    """Represents a parsed news article from a front page.

    This is the parser's output format, decoupled from database models.
    Position is assigned during parsing based on order of appearance.

    Attributes:
        headline: The article's main title.
        url: Full URL to the article page.
        summary: Brief description or subheadline. None if not available.
        image_url: URL of the associated image. None if not available.
        position: 1-based position on the page (1 = top/most prominent).
    """

    headline: str
    url: str
    position: int
    summary: str | None = None
    image_url: str | None = None


class Parser(Protocol):
    """Protocol for site-specific HTML parsers.

    Each news site requires a parser implementation that knows how to
    extract articles from that site's HTML structure.
    """

    def parse(self, html: str) -> list[ParsedArticle]:
        """Parse HTML and extract articles.

        Args:
            html: Raw HTML content from the site's front page.

        Returns:
            List of ParsedArticle objects extracted from the page.
            Empty list if no articles found. Articles include position
            based on order of appearance (1 = first/top).
        """
        ...
```

### 2. Update Infobae Parser

**File:** `src/news_scraper/parsers/infobae.py`

Update to use `ParsedArticle` and assign positions.

**Change 1:** Update import:

```python
# Replace:
from news_scraper.parsers.base import Article

# With:
from news_scraper.parsers.base import ParsedArticle
```

**Change 2:** Update `parse()` method to track position:

```python
def parse(self, html: str) -> list[ParsedArticle]:
    """Parse Infobae HTML and extract articles.

    Extracts ALL articles found on the page, deduplicates by URL
    (keeping first occurrence), assigns positions, and logs errors
    for individual articles that fail to parse.

    Args:
        html: Raw HTML content from Infobae's front page.

    Returns:
        List of unique ParsedArticle objects with positions.
        Empty list if no articles found.
    """
    log = get_logger()
    soup = BeautifulSoup(html, "lxml")
    articles: list[ParsedArticle] = []
    seen_urls: set[str] = set()
    position = 0  # Will be incremented before use (1-based)

    # Find all story card containers
    article_elements = soup.find_all(class_="story-card-ctn")

    for element in article_elements:
        if not isinstance(element, Tag):
            continue

        try:
            parsed = self._parse_article_element(element)
            if parsed and parsed["url"] not in seen_urls:
                position += 1
                articles.append(
                    ParsedArticle(
                        headline=parsed["headline"],
                        url=parsed["url"],
                        position=position,
                        summary=parsed.get("summary"),
                        image_url=parsed.get("image_url"),
                    )
                )
                seen_urls.add(parsed["url"])
        except Exception:
            # Log error with stack trace and continue with next article
            log.exception("Failed to parse article element")
            continue

    return articles
```

**Change 3:** Update `_parse_article_element()` to return dict instead of `ParsedArticle`:

```python
def _parse_article_element(self, element: Tag) -> dict[str, str | None] | None:
    """Extract article data from a story-card-ctn element.

    Args:
        element: BeautifulSoup Tag containing article data.

    Returns:
        Dict with article fields if extraction successful, None otherwise.
    """
    headline = self._extract_headline(element)
    url = self._extract_url(element)

    # Headline and URL are required
    if not headline or not url:
        return None

    summary = self._extract_summary(element)
    image_url = self._extract_image_url(element)

    return {
        "headline": headline,
        "url": url,
        "summary": summary,
        "image_url": image_url,
    }
```

### 3. Update Parser Registry

**File:** `src/news_scraper/parsers/__init__.py`

Update exports.

```python
"""Parsers module for extracting articles from news site HTML."""

from news_scraper.parsers.base import ParsedArticle, Parser
from news_scraper.parsers.infobae import InfobaeParser

__all__ = ["ParsedArticle", "Parser", "get_parser", "ParserNotFoundError"]

# Registry mapping source names to parser instances
# Using instances avoids typing issues with type[Protocol]
_PARSERS: dict[str, Parser] = {
    "infobae": InfobaeParser(),
}


class ParserNotFoundError(Exception):
    """Raised when no parser is registered for a source."""

    def __init__(self, source_name: str) -> None:
        """Initialize ParserNotFoundError.

        Args:
            source_name: Name of the source that has no parser.
        """
        self.source_name = source_name
        super().__init__(f"No parser registered for source: {source_name}")


def get_parser(source_name: str) -> Parser:
    """Get the parser instance for a source.

    Args:
        source_name: Name of the news source (e.g., "infobae").

    Returns:
        Parser instance that can parse that source's HTML.

    Raises:
        ParserNotFoundError: If no parser is registered for the source.
    """
    parser = _PARSERS.get(source_name.lower())
    if parser is None:
        raise ParserNotFoundError(source_name)
    return parser
```

### 4. Create Article Model

**File:** `src/news_scraper/db/models/article.py`

```python
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
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id"), nullable=False
    )
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
```

**Note:** Add `from typing import TYPE_CHECKING` at top of file.

### 5. Update Source Model with Relationship

**File:** `src/news_scraper/db/models/source.py`

Add back-reference to articles.

**Change 1:** Add import at top:

```python
from typing import TYPE_CHECKING

# ... existing imports ...

if TYPE_CHECKING:
    from news_scraper.db.models.article import Article
```

**Change 2:** Add relationship after existing fields:

```python
# Relationships
articles: Mapped[list["Article"]] = relationship(
    back_populates="source", cascade="all, delete-orphan"
)
```

### 6. Update Model Exports

**File:** `src/news_scraper/db/models/__init__.py`

```python
"""Model exports."""

from news_scraper.db.models.article import Article
from news_scraper.db.models.source import Source

__all__ = ["Article", "Source"]
```

### 7. Create Migration

**File:** `alembic/versions/<revision>_create_articles_table.py`

Generate with: `uv run alembic revision --autogenerate -m "create articles table"`

The autogenerated migration should look similar to:

```python
"""create articles table

Revision ID: <generated>
Revises: bcd78a54e570
Create Date: <generated>

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "<generated>"
down_revision: str | Sequence[str] | None = "bcd78a54e570"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create articles table."""
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("headline", sa.String(length=1024), nullable=False),
        sa.Column("description", sa.String(length=4096), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column(
            "last_seen_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index("ix_articles_url", "articles", ["url"], unique=False)
    op.create_index("ix_articles_source_id", "articles", ["source_id"], unique=False)
    op.create_index("ix_articles_last_seen_at", "articles", ["last_seen_at"], unique=False)


def downgrade() -> None:
    """Drop articles table."""
    op.drop_index("ix_articles_last_seen_at", table_name="articles")
    op.drop_index("ix_articles_source_id", table_name="articles")
    op.drop_index("ix_articles_url", table_name="articles")
    op.drop_table("articles")
```

After creating migration, run: `uv run alembic upgrade head`

### 8. Create Article Repository

**File:** `src/news_scraper/db/repositories/__init__.py`

```python
"""Repository exports."""

from news_scraper.db.repositories.article import ArticleRepository

__all__ = ["ArticleRepository"]
```

**File:** `src/news_scraper/db/repositories/article.py`

Repository pattern for article persistence with upsert logic.

```python
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
        self._log.debug("Updated existing article", url=parsed.url, position=parsed.position)
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

        for parsed in parsed_articles:
            existing = self._find_by_url(parsed.url)

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
```

### 9. Update Scraper Module

**File:** `src/news_scraper/scraper.py`

Update to persist articles and return summary stats.

```python
"""Scraper module for news sources."""

from dataclasses import dataclass
from datetime import datetime

from rich.console import Console
from rich.markup import escape

from news_scraper.browser import BrowserError, fetch_rendered_html
from news_scraper.db import get_session
from news_scraper.db.models import Source
from news_scraper.db.repositories import ArticleRepository
from news_scraper.logging import get_logger
from news_scraper.parsers import ParsedArticle, ParserNotFoundError, get_parser

# Display configuration
SUMMARY_MAX_LENGTH = 200

console = Console()


class ScraperError(Exception):
    """Exception raised when scraping fails."""

    def __init__(self, message: str, source_name: str) -> None:
        """Initialize ScraperError.

        Args:
            message: Error description.
            source_name: The source that failed to scrape.
        """
        self.message = message
        self.source_name = source_name
        super().__init__(message)


@dataclass
class ScrapeResult:
    """Result of a scrape operation.

    Attributes:
        articles: List of parsed articles.
        created_count: Number of new articles created.
        updated_count: Number of existing articles updated.
        skipped_count: Number of articles skipped (cross-source duplicates).
    """

    articles: list[ParsedArticle]
    created_count: int
    updated_count: int
    skipped_count: int


def scrape(source: Source) -> ScrapeResult:
    """Scrape news from the given source and persist to database.

    Fetches the source URL using a headless browser, parses the HTML
    to extract articles, persists them to the database, and returns
    the results.

    Args:
        source: The source to scrape.

    Returns:
        ScrapeResult with parsed articles and persistence stats.

    Raises:
        ScraperError: If fetching or parsing the page fails.
    """
    log = get_logger()
    log.info("Fetching page with headless browser", url=source.url)

    try:
        html = fetch_rendered_html(source.url)
    except BrowserError as e:
        log.error("Failed to fetch page", url=source.url, error=e.message)
        raise ScraperError(e.message, source.name) from e

    log.info("Page fetched successfully", html_length=len(html))

    try:
        parser = get_parser(source.name)
    except ParserNotFoundError as e:
        log.error("No parser for source", source=source.name)
        raise ScraperError(str(e), source.name) from e

    articles = parser.parse(html)
    log.info("Articles parsed", count=len(articles))

    # Persist to database
    seen_at = datetime.now()
    with get_session() as session:
        repo = ArticleRepository(session)
        created, updated, skipped = repo.bulk_upsert_from_parsed(
            articles, source, seen_at
        )
        session.commit()

    log.info(
        "Articles persisted",
        created=created,
        updated=updated,
        skipped=skipped,
    )

    return ScrapeResult(
        articles=articles,
        created_count=created,
        updated_count=updated,
        skipped_count=skipped,
    )


def format_article(article: ParsedArticle, index: int) -> str:
    """Format an article for console output.

    Args:
        article: The article to format.
        index: 1-based index for display.

    Returns:
        Formatted string representation of the article.
    """
    # Escape Rich markup in user-provided content to prevent corruption
    headline = escape(article.headline)
    url = escape(article.url)

    lines = [
        f"[{index}] {headline}",
        f"    URL: {url}",
        f"    Position: {article.position}",
    ]
    if article.summary:
        # Truncate long summaries for display
        if len(article.summary) > SUMMARY_MAX_LENGTH:
            summary = article.summary[:SUMMARY_MAX_LENGTH] + "..."
        else:
            summary = article.summary
        lines.append(f"    Summary: {escape(summary)}")
    if article.image_url:
        lines.append(f"    Image: {escape(article.image_url)}")
    return "\n".join(lines)


def print_scrape_result(result: ScrapeResult) -> None:
    """Print scrape result to console in a readable format.

    Args:
        result: Scrape result to print.
    """
    if not result.articles:
        console.print("No articles found.")
        return

    console.print(f"\nFound {len(result.articles)} articles:\n")
    console.print(f"  New: {result.created_count}")
    console.print(f"  Updated: {result.updated_count}")
    if result.skipped_count > 0:
        console.print(f"  Skipped (cross-source duplicates): {result.skipped_count}")
    console.print()
    console.print("=" * 80)
    for i, article in enumerate(result.articles, 1):
        console.print(format_article(article, i))
        console.print("-" * 80)
```

### 10. Update CLI Module

**File:** `src/news_scraper/cli.py`

Update to use new scrape result.

**Change 1:** Update import:

```python
# Replace:
from news_scraper.scraper import ScraperError, print_articles, scrape

# With:
from news_scraper.scraper import ScraperError, print_scrape_result, scrape
```

**Change 2:** Update scraping call in `main()`:

```python
# Replace:
        articles = scrape(source)
        print_articles(articles)

# With:
        result = scrape(source)
        print_scrape_result(result)
```

### 11. Tests

**File:** `tests/db/models/__init__.py`

```python
"""Tests for database models."""
```

**File:** `tests/db/models/test_article.py`

```python
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

    def test_url_unique_constraint(
        self, db_session: Session, source: Source
    ) -> None:
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

    def test_source_relationship(
        self, db_session: Session, source: Source
    ) -> None:
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
```

**File:** `tests/db/repositories/__init__.py`

```python
"""Tests for repositories."""
```

**File:** `tests/db/repositories/test_article.py`

```python
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
```

**File:** `tests/parsers/test_base.py` (Updated)

Update to use `ParsedArticle`:

```python
"""Tests for parser base classes."""

import pytest

from news_scraper.parsers.base import ParsedArticle


class TestParsedArticle:
    """Tests for ParsedArticle dataclass."""

    def test_article_with_all_fields(self) -> None:
        """Test creating article with all fields."""
        article = ParsedArticle(
            headline="Test Headline",
            url="https://example.com/article",
            position=1,
            summary="Test summary",
            image_url="https://example.com/image.jpg",
        )

        assert article.headline == "Test Headline"
        assert article.url == "https://example.com/article"
        assert article.position == 1
        assert article.summary == "Test summary"
        assert article.image_url == "https://example.com/image.jpg"

    def test_article_with_required_fields_only(self) -> None:
        """Test creating article with only required fields."""
        article = ParsedArticle(
            headline="Test Headline",
            url="https://example.com/article",
            position=5,
        )

        assert article.headline == "Test Headline"
        assert article.url == "https://example.com/article"
        assert article.position == 5
        assert article.summary is None
        assert article.image_url is None

    def test_article_is_frozen(self) -> None:
        """Test that ParsedArticle is immutable."""
        article = ParsedArticle(headline="Test", url="https://example.com", position=1)

        with pytest.raises(AttributeError):
            article.headline = "Modified"  # type: ignore[misc]

    def test_article_is_hashable(self) -> None:
        """Test that ParsedArticle can be used in sets."""
        article1 = ParsedArticle(headline="Test", url="https://example.com", position=1)
        article2 = ParsedArticle(headline="Test", url="https://example.com", position=1)

        article_set = {article1, article2}
        assert len(article_set) == 1
```

**File:** `tests/parsers/test_infobae.py` (Updated)

Update all tests to use `ParsedArticle` and verify position. Key changes:

```python
# Update import at top:
from news_scraper.parsers.base import ParsedArticle

# Update all assertions to include position checks, e.g.:
def test_parse_single_story_card(self, parser: InfobaeParser) -> None:
    """Test parsing HTML with a single story card."""
    html = """
    <html>
    <body>
        <a class="story-card-ctn" href="/politica/2026/01/25/test-article/">
            <h2 class="story-card-hl">Test Headline</h2>
        </a>
    </body>
    </html>
    """
    result = parser.parse(html)

    assert len(result) == 1
    assert result[0].headline == "Test Headline"
    assert result[0].url == "https://www.infobae.com/politica/2026/01/25/test-article/"
    assert result[0].position == 1

def test_parse_multiple_story_cards(self, parser: InfobaeParser) -> None:
    """Test parsing HTML with multiple story cards."""
    html = """
    <html>
    <body>
        <a class="story-card-ctn" href="/first-article/">
            <h2 class="story-card-hl">First Article</h2>
        </a>
        <a class="story-card-ctn" href="/second-article/">
            <h2 class="story-card-hl">Second Article</h2>
        </a>
    </body>
    </html>
    """
    result = parser.parse(html)

    assert len(result) == 2
    assert result[0].headline == "First Article"
    assert result[0].position == 1
    assert result[1].headline == "Second Article"
    assert result[1].position == 2

def test_parse_deduplicates_by_url_keeps_first_position(
    self, parser: InfobaeParser
) -> None:
    """Test that duplicate URLs keep first occurrence position."""
    html = """
    <html>
    <body>
        <a class="story-card-ctn" href="/same-article/">
            <h2 class="story-card-hl">First Instance</h2>
        </a>
        <a class="story-card-ctn" href="/same-article/">
            <h2 class="story-card-hl">Second Instance</h2>
        </a>
        <a class="story-card-ctn" href="/different-article/">
            <h2 class="story-card-hl">Different Article</h2>
        </a>
    </body>
    </html>
    """
    result = parser.parse(html)

    # Should only have 2 unique articles
    assert len(result) == 2
    # First article keeps position 1
    assert result[0].url == "https://www.infobae.com/same-article/"
    assert result[0].position == 1
    # Different article gets position 2 (not 3)
    assert result[1].url == "https://www.infobae.com/different-article/"
    assert result[1].position == 2
```

**File:** `tests/test_scraper.py` (Updated)

Update to test new `ScrapeResult` and persistence:

```python
"""Tests for the scraper module."""

from unittest.mock import MagicMock, patch

import pytest

from news_scraper.db.models import Source
from news_scraper.parsers import ParsedArticle, ParserNotFoundError
from news_scraper.scraper import (
    SUMMARY_MAX_LENGTH,
    ScrapeResult,
    format_article,
    print_scrape_result,
    scrape,
)


class TestScrape:
    """Tests for the scrape function."""

    def test_scrape_returns_scrape_result(self) -> None:
        """Test scrape returns ScrapeResult with stats."""
        source = Source(name="infobae", url="https://www.infobae.com")
        source.id = 1
        mock_html = "<html></html>"
        expected_articles = [
            ParsedArticle(
                headline="Test", url="https://www.infobae.com/test", position=1
            )
        ]

        with patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch:
            with patch("news_scraper.scraper.get_parser") as mock_get_parser:
                with patch("news_scraper.scraper.get_session") as mock_get_session:
                    mock_fetch.return_value = mock_html
                    mock_parser = MagicMock()
                    mock_parser.parse.return_value = expected_articles
                    mock_get_parser.return_value = mock_parser

                    # Mock session and repository
                    mock_session = MagicMock()
                    mock_get_session.return_value.__enter__.return_value = mock_session
                    with patch(
                        "news_scraper.scraper.ArticleRepository"
                    ) as mock_repo_class:
                        mock_repo = MagicMock()
                        mock_repo.bulk_upsert_from_parsed.return_value = (1, 0, 0)
                        mock_repo_class.return_value = mock_repo

                        result = scrape(source)

                        assert isinstance(result, ScrapeResult)
                        assert result.articles == expected_articles
                        assert result.created_count == 1
                        assert result.updated_count == 0
                        assert result.skipped_count == 0

    def test_scrape_raises_for_unknown_source(self) -> None:
        """Test scrape raises ScraperError for unknown source."""
        source = Source(name="unknown", url="https://unknown.com")

        with patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch:
            with patch("news_scraper.scraper.get_parser") as mock_get_parser:
                mock_fetch.return_value = "<html></html>"
                mock_get_parser.side_effect = ParserNotFoundError("unknown")

                from news_scraper.scraper import ScraperError

                with pytest.raises(ScraperError):
                    scrape(source)


class TestFormatArticle:
    """Tests for format_article function."""

    def test_format_article_includes_position(self) -> None:
        """Test formatting includes position."""
        article = ParsedArticle(
            headline="Test Headline", url="https://example.com", position=5
        )
        result = format_article(article, 1)

        assert "Position: 5" in result


class TestPrintScrapeResult:
    """Tests for print_scrape_result function."""

    def test_print_result_shows_counts(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing shows article counts."""
        result = ScrapeResult(
            articles=[
                ParsedArticle(headline="Test", url="https://example.com/1", position=1),
            ],
            created_count=5,
            updated_count=3,
            skipped_count=0,
        )
        print_scrape_result(result)
        captured = capsys.readouterr()

        assert "New: 5" in captured.out
        assert "Updated: 3" in captured.out

    def test_print_result_shows_skipped_when_nonzero(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing shows skipped count when > 0."""
        result = ScrapeResult(
            articles=[
                ParsedArticle(headline="Test", url="https://example.com/1", position=1),
            ],
            created_count=5,
            updated_count=3,
            skipped_count=2,
        )
        print_scrape_result(result)
        captured = capsys.readouterr()

        assert "Skipped" in captured.out
        assert "2" in captured.out
```

### 12. Update Project Structure Documentation

**File:** `docs/project-structure.md`

Add repositories directory:

```markdown
├── src/news_scraper/     # Source code
│   ├── ...
│   └── db/               # Database module
│       ├── __init__.py   # Module exports
│       ├── base.py       # DeclarativeBase + mixins
│       ├── session.py    # Engine and session management
│       ├── models/       # ORM models
│       │   ├── __init__.py
│       │   ├── source.py
│       │   └── article.py
│       └── repositories/ # Data access layer
│           ├── __init__.py
│           └── article.py
```

## File Summary

**New files:**
- `src/news_scraper/db/models/article.py` - Article SQLAlchemy model
- `src/news_scraper/db/repositories/__init__.py` - Repository exports
- `src/news_scraper/db/repositories/article.py` - ArticleRepository with upsert logic
- `alembic/versions/<revision>_create_articles_table.py` - Migration for articles table
- `tests/db/models/__init__.py` - Model tests package
- `tests/db/models/test_article.py` - Article model tests
- `tests/db/repositories/__init__.py` - Repository tests package
- `tests/db/repositories/test_article.py` - ArticleRepository tests

**Modified files:**
- `src/news_scraper/parsers/base.py` - Rename `Article` to `ParsedArticle`, add `position` field
- `src/news_scraper/parsers/infobae.py` - Use `ParsedArticle`, assign positions
- `src/news_scraper/parsers/__init__.py` - Export `ParsedArticle`
- `src/news_scraper/db/models/__init__.py` - Export `Article`
- `src/news_scraper/db/models/source.py` - Add `articles` relationship
- `src/news_scraper/scraper.py` - Add `ScrapeResult`, persist articles, update output
- `src/news_scraper/cli.py` - Use `print_scrape_result`
- `tests/parsers/test_base.py` - Update for `ParsedArticle`
- `tests/parsers/test_infobae.py` - Update for `ParsedArticle`, test positions
- `tests/test_scraper.py` - Update for `ScrapeResult`
- `docs/project-structure.md` - Document repositories

## Acceptance Criteria

### Article Model
- [ ] `Article` model created with all required fields
- [ ] `url` has unique constraint and index
- [ ] `source_id` foreign key to Source (NOT NULL)
- [ ] `last_seen_at` defaults to current timestamp
- [ ] Inherits `TimestampMixin` for `created_at`/`updated_at`
- [ ] Relationship to Source with back-reference

### Parser Changes
- [ ] `Article` dataclass renamed to `ParsedArticle`
- [ ] `ParsedArticle` includes `position` field (1-based)
- [ ] `InfobaeParser.parse()` assigns sequential positions
- [ ] Deduplication keeps first occurrence (lowest position)

### Persistence
- [ ] `ArticleRepository` created with `upsert_from_parsed()`
- [ ] `bulk_upsert_from_parsed()` for batch operations
- [ ] New articles created with all fields
- [ ] Existing articles (same source) updated with new data
- [ ] Cross-source duplicates logged and skipped
- [ ] `last_seen_at` updated on every scrape

### CLI Output
- [ ] Shows count of new articles created
- [ ] Shows count of updated articles
- [ ] Shows count of skipped articles (only if > 0)
- [ ] Article display includes position

### Quality
- [ ] All tests pass (`uv run pytest`)
- [ ] mypy passes with strict mode
- [ ] ruff passes
- [ ] pre-commit passes (`uv run pre-commit run --all-files`)
- [ ] Migration applies and rolls back cleanly

## Open Questions

None.

## Resolved Decisions

1. **URL as unique constraint, not PK**: Standard auto-increment `id` as PK, `url` with unique constraint and index for fast lookups. No need for URL hashing on SQLite.

2. **Source relationship**: `source_id` FK is NOT NULL. Articles always belong to a source.

3. **Cross-source duplicates**: If URL exists from different source, log warning and skip. Don't create duplicate.

4. **Position semantics**: 1-based, first/top article = position 1. Within same scrape, first occurrence wins. Updated on re-scrape.

5. **Field updates on re-scrape**: All fields updated except `url` (which is the identifier) and `created_at`.

6. **Dataclass vs Model separation**: Keep `ParsedArticle` dataclass for parser output, `Article` SQLAlchemy model for persistence. Parsers don't know about DB.

## Future Work (Not in This Spec)

- Add indexes for common query patterns (e.g., position by source)
- Batch insert optimization (bulk_insert_mappings)
- Track position history / movement over time
- Add parsers for other news sites
- CLI flag to show only new articles
- Export articles to JSON/CSV
