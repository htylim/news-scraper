# S005: Add Infobae Scraping - Part 2 (HTML Parsing)

Parse rendered HTML to extract article data and print structured output to console.

## Goal

Extend the scraper to parse Infobae's front page HTML and extract article information:

```bash
news-scraper -s infobae
```

The command will:
1. Fetch rendered HTML (existing Part 1 behavior)
2. Parse HTML to extract articles
3. Print structured article data to console (replaces raw HTML output)

Each article includes:
- **Headline**: Main title text
- **URL**: Link to full article
- **Summary**: Brief description/subheadline (optional - not all articles have one)
- **Image URL**: Associated image (optional - not all articles have one)

## Architecture

### Design Pattern: Strategy

Different news sites have different HTML structures. Use the Strategy pattern to allow site-specific parsing logic while maintaining a common interface.

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│   scraper   │────>│   Parser    │<────│  InfobaeParser   │
│             │     │  (Protocol) │     │                  │
└─────────────┘     └─────────────┘     └──────────────────┘
                           △
                           │
                    ┌──────┴──────┐
                    │ Future sites │
                    │ (Clarin, etc)│
                    └─────────────┘
```

Benefits:
- **Open/Closed Principle**: Add new sites without modifying existing code
- **Single Responsibility**: Each parser handles one site's structure
- **Testability**: Parsers can be unit tested in isolation with sample HTML

### Module Structure

```
src/news_scraper/
├── parsers/
│   ├── __init__.py      # Exports: Parser, Article, get_parser
│   ├── base.py          # Parser protocol + Article dataclass
│   └── infobae.py       # InfobaeParser implementation
└── scraper.py           # Updated to use parsers
```

## Deliverables

### 1. Add BeautifulSoup Dependency

**File:** `pyproject.toml`

Add beautifulsoup4 with lxml parser for HTML parsing:

```toml
dependencies = [
    "typer",
    "rich",
    "structlog",
    "sqlalchemy>=2.0.46",
    "alembic>=1.18.1",
    "playwright>=1.57.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
]
```

**Why BeautifulSoup + lxml:**
- BeautifulSoup: Industry-standard HTML parsing, handles malformed HTML gracefully
- lxml: Fast C-based parser, better performance than html.parser

### 2. Parser Base Module

**File:** `src/news_scraper/parsers/base.py`

Define the `Article` data model and `Parser` protocol.

```python
"""Base classes for HTML parsers."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Article:
    """Represents a parsed news article from a front page.

    Attributes:
        headline: The article's main title.
        url: Full URL to the article page.
        summary: Brief description or subheadline. None if not available.
        image_url: URL of the associated image. None if not available.
    """

    headline: str
    url: str
    summary: str | None = None
    image_url: str | None = None


class Parser(Protocol):
    """Protocol for site-specific HTML parsers.

    Each news site requires a parser implementation that knows how to
    extract articles from that site's HTML structure.
    """

    def parse(self, html: str) -> list[Article]:
        """Parse HTML and extract articles.

        Args:
            html: Raw HTML content from the site's front page.

        Returns:
            List of Article objects extracted from the page.
            Empty list if no articles found.
        """
        ...
```

Design notes:
- `Article` is a frozen dataclass (immutable, hashable)
- Optional fields use `None` default (not all articles have summaries/images)
- `Parser` is a `Protocol` (structural subtyping) - enables duck typing without inheritance
- Registry stores parser instances to avoid `type[Protocol]` typing issues with mypy

### 3. Infobae Parser Implementation

**File:** `src/news_scraper/parsers/infobae.py`

Infobae-specific parsing logic based on real HTML structure analysis.

**Infobae HTML Structure (as of Jan 2026):**
- Article container: `<a class="story-card-ctn" href="...">` (link tag with class)
- Headline: `<h2 class="story-card-hl">`
- Summary/deck: `<h3 class="story-card-deck">` (optional, not all articles have it)
- Image: `<img class="story-card-img" src="...">` (may have multiple classes like `"global-image story-card-img"`)
- URL: `href` attribute on the container `<a>` tag

**Note on class matching:** BeautifulSoup's `find(class_="story-card-img")` performs partial matching - it finds elements where "story-card-img" is one of potentially multiple CSS classes (e.g., `class="global-image story-card-img"`).

```python
"""Parser for Infobae news site."""

from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from news_scraper.logging import get_logger
from news_scraper.parsers.base import Article

# Base URL for resolving relative links
BASE_URL = "https://www.infobae.com"


class InfobaeParser:
    """Parser for Infobae front page HTML.

    Extracts articles from Infobae's HTML structure. Articles are identified
    by elements with class "story-card-ctn".
    """

    def parse(self, html: str) -> list[Article]:
        """Parse Infobae HTML and extract articles.

        Extracts ALL articles found on the page, deduplicates by URL,
        and logs errors for individual articles that fail to parse.

        Args:
            html: Raw HTML content from Infobae's front page.

        Returns:
            List of unique Article objects. Empty list if no articles found.
        """
        log = get_logger()
        soup = BeautifulSoup(html, "lxml")
        articles: list[Article] = []
        seen_urls: set[str] = set()

        # Find all story card containers
        article_elements = soup.find_all(class_="story-card-ctn")

        for element in article_elements:
            if not isinstance(element, Tag):
                continue

            try:
                article = self._parse_article_element(element)
                if article and article.url not in seen_urls:
                    articles.append(article)
                    seen_urls.add(article.url)
            except Exception as e:
                # Log error and continue with next article
                log.warning("Failed to parse article element", error=str(e))
                continue

        return articles

    def _parse_article_element(self, element: Tag) -> Article | None:
        """Extract article data from a story-card-ctn element.

        Args:
            element: BeautifulSoup Tag containing article data.

        Returns:
            Article object if extraction successful, None otherwise.
        """
        headline = self._extract_headline(element)
        url = self._extract_url(element)

        # Headline and URL are required
        if not headline or not url:
            return None

        summary = self._extract_summary(element)
        image_url = self._extract_image_url(element)

        return Article(
            headline=headline,
            url=url,
            summary=summary,
            image_url=image_url,
        )

    def _extract_headline(self, element: Tag) -> str | None:
        """Extract headline text from article element.

        Args:
            element: Article container Tag.

        Returns:
            Headline text or None if not found.
        """
        # Primary: Look for h2 with story-card-hl class
        h2 = element.find("h2", class_="story-card-hl")
        if h2:
            text = h2.get_text(strip=True)
            if text:
                return text

        # Fallback: any h2 or h3
        for tag_name in ["h2", "h3"]:
            heading = element.find(tag_name)
            if heading:
                text = heading.get_text(strip=True)
                if text:
                    return text

        return None

    def _extract_url(self, element: Tag) -> str | None:
        """Extract article URL from element.

        Only accepts URLs from the same domain (relative or absolute to BASE_URL).
        External or unexpected URLs are logged and skipped.

        Args:
            element: Article container Tag.

        Returns:
            Absolute URL or None if not found or rejected.
        """
        log = get_logger()

        # The story-card-ctn is an <a> tag itself with href
        href = element.get("href")
        if href and isinstance(href, str):
            resolved = self._resolve_article_url(href)
            if resolved:
                return resolved
            log.debug("Rejected URL from href attribute", href=href)

        # Fallback: find nested link
        link = element.find("a", href=True)
        if link:
            href = link.get("href")
            if href and isinstance(href, str):
                resolved = self._resolve_article_url(href)
                if resolved:
                    return resolved
                log.debug("Rejected URL from nested link", href=href)

        return None

    def _resolve_article_url(self, href: str) -> str | None:
        """Resolve href to absolute URL if it's from the same domain.

        Args:
            href: URL string (relative or absolute).

        Returns:
            Absolute URL if valid, None if external/rejected.
        """
        if href.startswith("/"):
            return urljoin(BASE_URL, href)
        elif href.startswith(BASE_URL):
            return href
        return None

    def _extract_summary(self, element: Tag) -> str | None:
        """Extract summary/deck from article element.

        Args:
            element: Article container Tag.

        Returns:
            Summary text or None if not found.
        """
        # Look for h3 with story-card-deck class
        deck = element.find("h3", class_="story-card-deck")
        if deck:
            text = deck.get_text(strip=True)
            if text:
                return text

        return None

    def _extract_image_url(self, element: Tag) -> str | None:
        """Extract image URL from article element.

        Args:
            element: Article container Tag.

        Returns:
            Absolute image URL or None if not found.
        """
        # Look for img with story-card-img class (partial match, may have other classes)
        img = element.find("img", class_="story-card-img")
        if not img:
            # Fallback: any img in the element
            img = element.find("img")

        if img:
            src = img.get("src")
            if src and isinstance(src, str):
                return self._resolve_image_url(src)

        return None

    def _resolve_image_url(self, url: str) -> str:
        """Resolve potentially relative image URL to absolute.

        Args:
            url: Image URL (may be relative or absolute).

        Returns:
            Absolute URL.
        """
        if url.startswith("//"):
            return f"https:{url}"
        elif url.startswith("/"):
            return urljoin(BASE_URL, url)
        return url
```

### 4. Parser Registry

**File:** `src/news_scraper/parsers/__init__.py`

Registry to map source names to their parser instances.

```python
"""Parsers module for extracting articles from news site HTML."""

from news_scraper.parsers.base import Article, Parser
from news_scraper.parsers.infobae import InfobaeParser

__all__ = ["Article", "Parser", "get_parser", "ParserNotFoundError"]

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

### 5. Update Scraper Module

**File:** `src/news_scraper/scraper.py`

Replace raw HTML output with parsed article output.

```python
"""Scraper module for news sources."""

from rich.console import Console

from news_scraper.browser import BrowserError, fetch_rendered_html
from news_scraper.db.models import Source
from news_scraper.logging import get_logger
from news_scraper.parsers import Article, ParserNotFoundError, get_parser

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


def scrape(source: Source) -> list[Article]:
    """Scrape news from the given source.

    Fetches the source URL using a headless browser, parses the HTML
    to extract articles, and returns the article data.

    Args:
        source: The source to scrape.

    Returns:
        List of Article objects extracted from the source.

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

    return articles


def format_article(article: Article, index: int) -> str:
    """Format an article for console output.

    Args:
        article: The article to format.
        index: 1-based index for display.

    Returns:
        Formatted string representation of the article.
    """
    lines = [
        f"[{index}] {article.headline}",
        f"    URL: {article.url}",
    ]
    if article.summary:
        # Truncate long summaries for display
        if len(article.summary) > SUMMARY_MAX_LENGTH:
            summary = article.summary[:SUMMARY_MAX_LENGTH] + "..."
        else:
            summary = article.summary
        lines.append(f"    Summary: {summary}")
    if article.image_url:
        lines.append(f"    Image: {article.image_url}")
    return "\n".join(lines)


def print_articles(articles: list[Article]) -> None:
    """Print articles to console in a readable format.

    Args:
        articles: List of articles to print.
    """
    if not articles:
        console.print("No articles found.")
        return

    console.print(f"\nFound {len(articles)} articles:\n")
    console.print("=" * 80)
    for i, article in enumerate(articles, 1):
        console.print(format_article(article, i))
        console.print("-" * 80)
```

### 6. Update CLI Module

**File:** `src/news_scraper/cli.py`

Update imports and main function to call `print_articles` instead of printing raw HTML.

**Change 1:** Update the import at the top of the file:

```python
# Replace:
from news_scraper.scraper import ScraperError, scrape

# With:
from news_scraper.scraper import ScraperError, print_articles, scrape
```

**Change 2:** Update the scraping call in `main()` function (around line 96):

```python
# Replace:
        log.info("Scraping source", source=normalized_name)
        try:
            scrape(source)
        except ScraperError as e:

# With:
        log.info("Scraping source", source=normalized_name)
        try:
            articles = scrape(source)
            print_articles(articles)
        except ScraperError as e:
```

### 7. Tests

**File:** `tests/parsers/__init__.py`

```python
"""Tests for parsers module."""
```

**File:** `tests/parsers/test_base.py`

```python
"""Tests for parser base classes."""

import pytest

from news_scraper.parsers.base import Article


class TestArticle:
    """Tests for Article dataclass."""

    def test_article_with_all_fields(self) -> None:
        """Test creating article with all fields."""
        article = Article(
            headline="Test Headline",
            url="https://example.com/article",
            summary="Test summary",
            image_url="https://example.com/image.jpg",
        )

        assert article.headline == "Test Headline"
        assert article.url == "https://example.com/article"
        assert article.summary == "Test summary"
        assert article.image_url == "https://example.com/image.jpg"

    def test_article_with_required_fields_only(self) -> None:
        """Test creating article with only required fields."""
        article = Article(
            headline="Test Headline",
            url="https://example.com/article",
        )

        assert article.headline == "Test Headline"
        assert article.url == "https://example.com/article"
        assert article.summary is None
        assert article.image_url is None

    def test_article_is_frozen(self) -> None:
        """Test that Article is immutable."""
        article = Article(headline="Test", url="https://example.com")

        with pytest.raises(AttributeError):
            article.headline = "Modified"  # type: ignore[misc]

    def test_article_is_hashable(self) -> None:
        """Test that Article can be used in sets."""
        article1 = Article(headline="Test", url="https://example.com")
        article2 = Article(headline="Test", url="https://example.com")

        article_set = {article1, article2}
        assert len(article_set) == 1
```

**File:** `tests/parsers/test_infobae.py`

```python
"""Tests for Infobae parser."""

from pathlib import Path

import pytest

from news_scraper.parsers.infobae import InfobaeParser


@pytest.fixture
def parser() -> InfobaeParser:
    """Create parser instance for tests."""
    return InfobaeParser()


class TestInfobaeParser:
    """Tests for InfobaeParser."""

    def test_parse_empty_html(self, parser: InfobaeParser) -> None:
        """Test parsing empty HTML returns empty list."""
        result = parser.parse("")
        assert result == []

    def test_parse_html_without_articles(self, parser: InfobaeParser) -> None:
        """Test parsing HTML with no article elements."""
        html = "<html><body><div>No articles here</div></body></html>"
        result = parser.parse(html)
        assert result == []

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
        assert result[1].headline == "Second Article"

    def test_parse_story_card_with_deck(self, parser: InfobaeParser) -> None:
        """Test parsing story card with summary/deck."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article-with-deck/">
                <h2 class="story-card-hl">Main Headline</h2>
                <h3 class="story-card-deck">This is the summary of the article.</h3>
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Main Headline"
        assert result[0].summary == "This is the summary of the article."

    def test_parse_story_card_with_image(self, parser: InfobaeParser) -> None:
        """Test parsing story card with image."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article-image/">
                <h2 class="story-card-hl">Article with Image</h2>
                <img class="story-card-img" src="https://example.com/image.jpg">
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://example.com/image.jpg"

    def test_parse_story_card_with_multiple_classes(self, parser: InfobaeParser) -> None:
        """Test parsing story card where img has multiple CSS classes."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article/">
                <h2 class="story-card-hl">Test</h2>
                <img class="global-image story-card-img" src="https://example.com/image.jpg">
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://example.com/image.jpg"

    def test_parse_deduplicates_by_url(self, parser: InfobaeParser) -> None:
        """Test that duplicate URLs are filtered out."""
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
        urls = [a.url for a in result]
        assert "https://www.infobae.com/same-article/" in urls
        assert "https://www.infobae.com/different-article/" in urls

    def test_parse_skips_card_without_headline(self, parser: InfobaeParser) -> None:
        """Test that cards without headlines are skipped."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/no-headline/">
                <img class="story-card-img" src="image.jpg">
            </a>
            <a class="story-card-ctn" href="/valid-article/">
                <h2 class="story-card-hl">Valid Article</h2>
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_handles_absolute_urls(self, parser: InfobaeParser) -> None:
        """Test parsing handles absolute URLs correctly."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="https://www.infobae.com/full/path/article/">
                <h2 class="story-card-hl">Absolute URL Article</h2>
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].url == "https://www.infobae.com/full/path/article/"

    def test_parse_skips_external_urls(self, parser: InfobaeParser) -> None:
        """Test that external URLs are rejected."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="https://other-site.com/article/">
                <h2 class="story-card-hl">External Article</h2>
            </a>
            <a class="story-card-ctn" href="/valid-article/">
                <h2 class="story-card-hl">Valid Article</h2>
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        # External URL should be skipped
        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_resolves_relative_image_url(self, parser: InfobaeParser) -> None:
        """Test parsing resolves relative image URLs."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article/">
                <h2 class="story-card-hl">Test</h2>
                <img class="story-card-img" src="/images/photo.jpg">
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://www.infobae.com/images/photo.jpg"

    def test_parse_resolves_protocol_relative_image_url(self, parser: InfobaeParser) -> None:
        """Test parsing resolves protocol-relative image URLs."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article/">
                <h2 class="story-card-hl">Test</h2>
                <img class="story-card-img" src="//cdn.example.com/image.jpg">
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://cdn.example.com/image.jpg"


class TestInfobaeParserHelpers:
    """Tests for InfobaeParser helper methods."""

    @pytest.fixture
    def parser(self) -> InfobaeParser:
        """Create parser instance for helper tests."""
        return InfobaeParser()

    def test_resolve_image_url_absolute(self, parser: InfobaeParser) -> None:
        """Test resolving absolute image URL."""
        url = "https://example.com/image.jpg"
        result = parser._resolve_image_url(url)
        assert result == url

    def test_resolve_image_url_relative(self, parser: InfobaeParser) -> None:
        """Test resolving relative image URL."""
        url = "/images/photo.jpg"
        result = parser._resolve_image_url(url)
        assert result == "https://www.infobae.com/images/photo.jpg"

    def test_resolve_image_url_protocol_relative(self, parser: InfobaeParser) -> None:
        """Test resolving protocol-relative image URL."""
        url = "//cdn.example.com/image.jpg"
        result = parser._resolve_image_url(url)
        assert result == "https://cdn.example.com/image.jpg"

    def test_resolve_article_url_relative(self, parser: InfobaeParser) -> None:
        """Test resolving relative article URL."""
        result = parser._resolve_article_url("/article/path/")
        assert result == "https://www.infobae.com/article/path/"

    def test_resolve_article_url_absolute(self, parser: InfobaeParser) -> None:
        """Test resolving absolute article URL."""
        result = parser._resolve_article_url("https://www.infobae.com/article/")
        assert result == "https://www.infobae.com/article/"

    def test_resolve_article_url_external_rejected(self, parser: InfobaeParser) -> None:
        """Test that external URLs return None."""
        result = parser._resolve_article_url("https://other-site.com/article/")
        assert result is None


class TestInfobaeParserRealHtml:
    """Integration tests using real HTML fixture from Infobae."""

    @pytest.fixture
    def parser(self) -> InfobaeParser:
        """Create parser instance for tests."""
        return InfobaeParser()

    @pytest.fixture
    def infobae_html(self) -> str:
        """Load real Infobae HTML fixture."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "infobae_sample.html"
        return fixture_path.read_text()

    def test_parse_real_html_extracts_articles(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test parsing real Infobae HTML extracts expected articles."""
        result = parser.parse(infobae_html)

        # Fixture contains 5 articles
        assert len(result) == 5

    def test_parse_real_html_first_article(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test first article from real HTML has expected data."""
        result = parser.parse(infobae_html)

        first = result[0]
        assert "gobernadores" in first.headline.lower()
        assert first.url.startswith("https://www.infobae.com/")
        assert first.summary is not None  # First article has a deck
        assert first.image_url is not None
        assert first.image_url.startswith("https://")

    def test_parse_real_html_all_have_headlines(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test all parsed articles have headlines."""
        result = parser.parse(infobae_html)

        for article in result:
            assert article.headline
            assert len(article.headline) > 10

    def test_parse_real_html_all_have_urls(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test all parsed articles have valid URLs."""
        result = parser.parse(infobae_html)

        for article in result:
            assert article.url
            assert article.url.startswith("https://www.infobae.com/")

    def test_parse_real_html_all_have_images(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test all parsed articles have image URLs."""
        result = parser.parse(infobae_html)

        for article in result:
            assert article.image_url
            assert article.image_url.startswith("https://")

    def test_parse_real_html_no_duplicates(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test no duplicate URLs in parsed results."""
        result = parser.parse(infobae_html)

        urls = [article.url for article in result]
        assert len(urls) == len(set(urls))
```

**File:** `tests/parsers/test_registry.py`

```python
"""Tests for parser registry."""

import pytest

from news_scraper.parsers import ParserNotFoundError, get_parser
from news_scraper.parsers.infobae import InfobaeParser


class TestGetParser:
    """Tests for get_parser function."""

    def test_get_infobae_parser(self) -> None:
        """Test getting Infobae parser returns instance."""
        parser = get_parser("infobae")
        assert isinstance(parser, InfobaeParser)

    def test_get_parser_case_insensitive(self) -> None:
        """Test parser lookup is case insensitive."""
        assert isinstance(get_parser("INFOBAE"), InfobaeParser)
        assert isinstance(get_parser("Infobae"), InfobaeParser)

    def test_get_parser_unknown_source(self) -> None:
        """Test getting parser for unknown source raises error."""
        with pytest.raises(ParserNotFoundError) as exc_info:
            get_parser("unknown_source")

        assert exc_info.value.source_name == "unknown_source"
        assert "unknown_source" in str(exc_info.value)
```

**File:** `tests/test_scraper.py` (Updated)

```python
"""Tests for the scraper module."""

from unittest.mock import MagicMock, patch

import pytest

from news_scraper.db.models import Source
from news_scraper.parsers import Article, ParserNotFoundError
from news_scraper.scraper import SUMMARY_MAX_LENGTH, format_article, print_articles, scrape


class TestScrape:
    """Tests for the scrape function."""

    def test_scrape_returns_articles(self) -> None:
        """Test scrape returns parsed articles."""
        source = Source(name="infobae", url="https://www.infobae.com")
        mock_html = "<html><body><article><h2>Test</h2><a href='/test'>Link</a></article></body></html>"
        expected_articles = [Article(headline="Test", url="https://www.infobae.com/test")]

        with patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch:
            with patch("news_scraper.scraper.get_parser") as mock_get_parser:
                mock_fetch.return_value = mock_html
                mock_parser = MagicMock()
                mock_parser.parse.return_value = expected_articles
                mock_get_parser.return_value = mock_parser

                result = scrape(source)

                assert result == expected_articles
                mock_fetch.assert_called_once_with("https://www.infobae.com")
                mock_parser.parse.assert_called_once_with(mock_html)

    def test_scrape_uses_source_url(self) -> None:
        """Test scrape passes source URL to fetch function."""
        source = Source(name="infobae", url="https://www.infobae.com")

        with patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch:
            with patch("news_scraper.scraper.get_parser") as mock_get_parser:
                mock_fetch.return_value = "<html></html>"
                mock_parser = MagicMock()
                mock_parser.parse.return_value = []
                mock_get_parser.return_value = mock_parser

                scrape(source)

                mock_fetch.assert_called_once_with("https://www.infobae.com")

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

    def test_format_article_basic(self) -> None:
        """Test formatting article with required fields only."""
        article = Article(headline="Test Headline", url="https://example.com")
        result = format_article(article, 1)

        assert "[1] Test Headline" in result
        assert "URL: https://example.com" in result

    def test_format_article_with_summary(self) -> None:
        """Test formatting article with summary."""
        article = Article(
            headline="Test",
            url="https://example.com",
            summary="This is a summary",
        )
        result = format_article(article, 1)

        assert "Summary: This is a summary" in result

    def test_format_article_with_image(self) -> None:
        """Test formatting article with image."""
        article = Article(
            headline="Test",
            url="https://example.com",
            image_url="https://example.com/image.jpg",
        )
        result = format_article(article, 1)

        assert "Image: https://example.com/image.jpg" in result

    def test_format_article_truncates_long_summary(self) -> None:
        """Test that long summaries are truncated at SUMMARY_MAX_LENGTH."""
        long_summary = "x" * (SUMMARY_MAX_LENGTH + 100)
        article = Article(headline="Test", url="https://example.com", summary=long_summary)
        result = format_article(article, 1)

        assert "..." in result
        # Summary line should contain truncated text
        assert f"{'x' * SUMMARY_MAX_LENGTH}..." in result

    def test_format_article_short_summary_not_truncated(self) -> None:
        """Test that short summaries are not truncated."""
        short_summary = "x" * (SUMMARY_MAX_LENGTH - 10)
        article = Article(headline="Test", url="https://example.com", summary=short_summary)
        result = format_article(article, 1)

        assert "..." not in result
        assert short_summary in result


class TestPrintArticles:
    """Tests for print_articles function."""

    def test_print_articles_empty(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test printing empty article list."""
        print_articles([])
        captured = capsys.readouterr()

        assert "No articles found" in captured.out

    def test_print_articles_shows_count(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test printing shows article count."""
        articles = [
            Article(headline="Test 1", url="https://example.com/1"),
            Article(headline="Test 2", url="https://example.com/2"),
        ]
        print_articles(articles)
        captured = capsys.readouterr()

        assert "Found 2 articles" in captured.out
```

### 8. Update Libraries Documentation

**File:** `docs/libraries.md`

Add new dependencies:

```markdown
## Runtime

- **typer** - CLI framework
- **rich** - Terminal output formatting
- **structlog** - Structured logging
- **sqlalchemy** - ORM with native type hints (2.0+)
- **alembic** - Database migrations
- **playwright** - Headless browser automation for JS-rendered pages
- **beautifulsoup4** - HTML parsing library
- **lxml** - Fast HTML/XML parser (backend for BeautifulSoup)
```

### 9. Update Project Structure Documentation

**File:** `docs/project-structure.md`

Add parsers module:

```markdown
├── src/news_scraper/     # Source code
│   ├── ...
│   ├── parsers/          # Site-specific HTML parsers
│   │   ├── __init__.py   # Parser registry
│   │   ├── base.py       # Parser protocol + Article model
│   │   └── infobae.py    # Infobae parser implementation
│   └── ...
```

## File Summary

**New files:**
- `src/news_scraper/parsers/__init__.py` - Parser registry and exports
- `src/news_scraper/parsers/base.py` - Article dataclass and Parser protocol
- `src/news_scraper/parsers/infobae.py` - Infobae-specific parser
- `tests/parsers/__init__.py` - Parser tests package
- `tests/parsers/test_base.py` - Article dataclass tests
- `tests/parsers/test_infobae.py` - Infobae parser tests (with real HTML integration tests)
- `tests/parsers/test_registry.py` - Parser registry tests
- `tests/fixtures/infobae_sample.html` - Real HTML fixture captured from Infobae (5 articles, pre-created during spec development)

**Modified files:**
- `pyproject.toml` - Add beautifulsoup4 and lxml dependencies
- `src/news_scraper/scraper.py` - Use parsers, return articles instead of printing HTML
- `src/news_scraper/cli.py` - Call print_articles with results
- `tests/test_scraper.py` - Update tests for new scraper behavior
- `docs/libraries.md` - Document new dependencies
- `docs/project-structure.md` - Document parsers module

## Acceptance Criteria

### CLI Functionality
- [ ] `news-scraper -s infobae` prints structured article list (not raw HTML)
- [ ] Each article shows: headline, URL, summary (if available), image URL (if available)
- [ ] Output shows total article count
- [ ] Unknown sources show appropriate error message
- [ ] Existing CLI flags (`--verbose`, `--version`, `--help`) still work

### Parser Architecture
- [ ] `Parser` protocol defined with `parse(self, html: str) -> list[Article]` signature
- [ ] `Article` dataclass is frozen (immutable) and hashable
- [ ] `get_parser()` function returns parser instance for source name
- [ ] `get_parser()` is case-insensitive
- [ ] `ParserNotFoundError` raised for unknown sources

### Infobae Parser
- [ ] Finds articles by `story-card-ctn` class
- [ ] Extracts headlines from `<h2 class="story-card-hl">` elements
- [ ] Extracts article URLs from `href` attribute on container element
- [ ] Extracts summaries from `<h3 class="story-card-deck">` when available
- [ ] Extracts image URLs from `<img class="story-card-img">` elements (handles multiple CSS classes)
- [ ] Resolves relative URLs to absolute (including protocol-relative `//`)
- [ ] Deduplicates articles by URL (keeps first occurrence)
- [ ] Logs warning and continues if individual article fails to parse
- [ ] Logs debug message when external/invalid URLs are rejected
- [ ] Skips articles without headline or URL
- [ ] Skips articles with external URLs (non-infobae domains)
- [ ] Returns empty list for HTML with no articles
- [ ] Integration tests pass against real HTML fixture

### Scraper Output
- [ ] `SUMMARY_MAX_LENGTH` constant defined for truncation limit
- [ ] Uses Rich `console.print()` for output (ADR-005 compliance)

### Quality
- [ ] All tests pass (`uv run pytest`)
- [ ] mypy passes with strict mode
- [ ] ruff passes
- [ ] pre-commit passes (`uv run pre-commit run --all-files`)

## Manual Verification

After implementation, manually verify using the browser agent (MCP cursor-ide-browser):

1. Navigate to https://www.infobae.com
2. Note visible headlines, images, and summaries for first 5 articles
3. Run `news-scraper -s infobae`
4. Verify extracted data matches what's visible in the browser
5. Document any discrepancies in implementation notes

## Resolved Decisions

1. **Article count**: Extract ALL articles found on the page.
2. **Duplicate articles**: Deduplicate by URL - skip articles with URLs already seen.
3. **Error tolerance**: Log errors and continue - if one article fails to parse, log the error and move to the next.

## Future Work (Not in This Spec)

- Store articles in database (Part 3)
- Add parsers for other news sites (Clarin, La Nacion, etc.)
- Handle pagination / infinite scroll
- Extract article categories/tags
- Extract author information
- Extract publication date
