# S007: Add La Nacion Scraping

Add La Nacion news source with parser implementation to scrape articles from the front page.

## Goal

Enable scraping from La Nacion (https://www.lanacion.com.ar/):

```bash
news-scraper -s lanacion
```

The command will:
1. Fetch rendered HTML from La Nacion front page
2. Parse HTML to extract articles using new `LaNacionParser`
3. Persist articles to database with deduplication
4. Print summary of new/updated articles to console

## Architecture

### Parser Strategy

Following the existing pattern (Infobae), create a site-specific parser that implements the `Parser` protocol.

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│   scraper   │────>│   Parser    │<────│  LaNacionParser  │
│             │     │  (Protocol) │     │                  │
└─────────────┘     └─────────────┘     └──────────────────┘
                           △
                           │
                    ┌──────┴──────┐
                    │ InfobaeParser│
                    └─────────────┘
```

### La Nacion HTML Structure (as of Jan 2026)

Based on browser inspection of https://www.lanacion.com.ar/:

**Article Container:**
- Element: `<article class="ln-card ...">`
- The `ln-card` class identifies article cards
- ~134 articles found on front page

**URL:**
- Inside article: `<a class="ln-link">` with `href` attribute
- URLs are relative (e.g., `/politica/el-conflicto-mundial-...`)
- Base URL: `https://www.lanacion.com.ar`

**Headline:**
- Featured articles use `<h1>` tag
- Regular articles use `<h2>` tag
- Headline text is inside these heading elements
- Some headlines have a prefix (e.g., "Análisis." or "\"Los de arriba sabían\".") followed by the main headline

**Summary:**
- `<h3>` element when present
- Only ~10 out of 134 articles have summaries
- Optional field

**Image:**
- `<img>` inside `<picture>` element
- Use `src` attribute (absolute URLs from CDN)
- Image `alt` attribute often contains a shorter version of headline

**Sample Article HTML:**

```html
<article class="ln-card flex flex-column ai-start --4xl --regular" data-id="6HD4MBYDCJAYPM4XOJEJKSFO6Q">
  <a class="link ln-link flex flex-column --unstyled" 
     href="/politica/el-conflicto-mundial-se-proyecta-sobre-lula-y-milei-nid28012026/"
     title="Análisis. El conflicto mundial se proyecta sobre Milei y Lula">
    <section class="media-container">
      <picture class="ln-placeholder">
        <img alt="El conflicto mundial se proyecta sobre Milei y Lula" 
             src="https://www.lanacion.com.ar/resizer/v2/...jpg" />
      </picture>
    </section>
    <section class="description-container">
      <h1>Análisis. El conflicto mundial se proyecta sobre Milei y Lula</h1>
      <h2>El Presidente argentino sigue a Donald Trump...</h2>
    </section>
  </a>
</article>
```

**Note on headline vs summary:**
- When article has both `<h1>` and `<h2>`: h1 = headline, h2 = summary
- When article has only `<h2>`: h2 = headline
- When article has `<h2>` and `<h3>`: h2 = headline, h3 = summary

## Deliverables

### 1. Add La Nacion Source to Database

**File:** `alembic/versions/<revision>_seed_lanacion_source.py`

Create migration to seed La Nacion source.

```python
"""seed lanacion source

Revision ID: <generated>
Revises: <previous_revision>
Create Date: <generated>
"""

from collections.abc import Sequence

from alembic import op

revision: str = "<generated>"
down_revision: str | Sequence[str] | None = "<previous_revision>"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Seed La Nacion source."""
    op.execute(
        """
        INSERT INTO sources (name, url, is_enabled, created_at, updated_at)
        VALUES (
            'lanacion',
            'https://www.lanacion.com.ar',
            1,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        """
    )


def downgrade() -> None:
    """Remove La Nacion source."""
    op.execute("DELETE FROM sources WHERE name = 'lanacion'")
```

After creating migration, run: `uv run alembic upgrade head`

### 2. Create La Nacion Parser

**File:** `src/news_scraper/parsers/lanacion.py`

Parser implementation for La Nacion's HTML structure.

```python
"""Parser for La Nacion news site."""

from typing import TypedDict
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from news_scraper.logging import get_logger
from news_scraper.parsers.base import ParsedArticle


class _ParsedData(TypedDict):
    """Internal type for parsed article data before creating ParsedArticle."""

    headline: str
    url: str
    summary: str | None
    image_url: str | None


# Base URL for resolving relative links
BASE_URL = "https://www.lanacion.com.ar"


class LaNacionParser:
    """Parser for La Nacion front page HTML.

    Extracts articles from La Nacion's HTML structure. Articles are identified
    by `<article>` elements with class "ln-card".
    """

    def parse(self, html: str) -> list[ParsedArticle]:
        """Parse La Nacion HTML and extract articles.

        Extracts ALL articles found on the page, deduplicates by URL
        (keeping first occurrence), assigns positions, and logs errors
        for individual articles that fail to parse.

        Args:
            html: Raw HTML content from La Nacion's front page.

        Returns:
            List of unique ParsedArticle objects with positions.
            Empty list if no articles found.
        """
        log = get_logger()
        soup = BeautifulSoup(html, "lxml")
        articles: list[ParsedArticle] = []
        seen_urls: set[str] = set()
        position = 0  # Will be incremented before use (1-based)

        # Find all article cards with ln-card class
        article_elements = soup.find_all("article", class_="ln-card")

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

    def _parse_article_element(self, element: Tag) -> _ParsedData | None:
        """Extract article data from an ln-card article element.

        Args:
            element: BeautifulSoup Tag containing article data.

        Returns:
            Dict with article fields if extraction successful, None otherwise.
        """
        url = self._extract_url(element)
        headline = self._extract_headline(element)

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

    def _extract_url(self, element: Tag) -> str | None:
        """Extract article URL from element.

        Looks for anchor with ln-link class and validates the URL is from
        La Nacion's domain.

        Args:
            element: Article container Tag.

        Returns:
            Absolute URL or None if not found or rejected.
        """
        log = get_logger()

        # Find anchor with ln-link class
        link = element.find("a", class_="ln-link")
        if link and isinstance(link, Tag):
            href = link.get("href")
            if href and isinstance(href, str):
                resolved = self._resolve_article_url(href)
                if resolved:
                    return resolved
                log.debug("Rejected URL from ln-link", href=href)

        # Fallback: any anchor with href
        link = element.find("a", href=True)
        if link and isinstance(link, Tag):
            href = link.get("href")
            if href and isinstance(href, str):
                resolved = self._resolve_article_url(href)
                if resolved:
                    return resolved
                log.debug("Rejected URL from fallback link", href=href)

        return None

    def _resolve_article_url(self, href: str) -> str | None:
        """Resolve href to absolute URL if it's from La Nacion's domain.

        Args:
            href: URL string (relative or absolute).

        Returns:
            Absolute URL if valid, None if external/rejected.
        """
        # Allowlist of valid La Nacion hostnames
        allowed_hosts = {"www.lanacion.com.ar", "lanacion.com.ar"}

        # Use urljoin to resolve relative and protocol-relative URLs
        resolved = urljoin(BASE_URL, href)
        parsed = urlparse(resolved)

        # Check if the resolved URL is from an allowed host
        if parsed.netloc in allowed_hosts:
            return resolved
        return None

    def _extract_headline(self, element: Tag) -> str | None:
        """Extract headline text from article element.

        La Nacion uses h1 for featured articles and h2 for regular articles.
        When both h1 and h2 exist, h1 is the headline.

        Args:
            element: Article container Tag.

        Returns:
            Headline text or None if not found.
        """
        # Try h1 first (featured articles)
        h1 = element.find("h1")
        if h1:
            text: str = h1.get_text(strip=True)
            if text:
                return text

        # Fall back to h2 (regular articles)
        h2 = element.find("h2")
        if h2:
            text = h2.get_text(strip=True)
            if text:
                return text

        return None

    def _extract_summary(self, element: Tag) -> str | None:
        """Extract summary from article element.

        Summary is in h3 when present. If article has h1+h2, the h2 is the summary.

        Args:
            element: Article container Tag.

        Returns:
            Summary text or None if not found.
        """
        # Check if article has both h1 (headline) and h2 (summary)
        h1 = element.find("h1")
        h2 = element.find("h2")

        if h1 and h2:
            # When h1 exists, h2 is the summary
            text: str = h2.get_text(strip=True)
            if text:
                return text

        # Otherwise, check for h3 as summary
        h3 = element.find("h3")
        if h3:
            text = h3.get_text(strip=True)
            if text:
                return text

        return None

    def _extract_image_url(self, element: Tag) -> str | None:
        """Extract image URL from article element.

        La Nacion uses picture elements with img inside.
        Images are typically served from CDN with absolute URLs.

        Args:
            element: Article container Tag.

        Returns:
            Absolute image URL or None if not found.
        """
        # Find img inside the article
        img = element.find("img")

        if img and isinstance(img, Tag):
            # Try src first (most common), then data-src for lazy loading
            for attr in ("src", "data-src"):
                src = img.get(attr)
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

### 3. Register La Nacion Parser

**File:** `src/news_scraper/parsers/__init__.py`

Add La Nacion parser to the registry.

```python
"""Parsers module for extracting articles from news site HTML."""

from news_scraper.parsers.base import ParsedArticle, Parser
from news_scraper.parsers.infobae import InfobaeParser
from news_scraper.parsers.lanacion import LaNacionParser

__all__ = ["ParsedArticle", "Parser", "get_parser", "ParserNotFoundError"]

# Registry mapping source names to parser instances
# Using instances avoids typing issues with type[Protocol]
_PARSERS: dict[str, Parser] = {
    "infobae": InfobaeParser(),
    "lanacion": LaNacionParser(),
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
        source_name: Name of the news source (e.g., "infobae", "lanacion").

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

### 4. Tests

**File:** `tests/parsers/test_lanacion.py`

```python
"""Tests for La Nacion parser."""

from pathlib import Path

import pytest

from news_scraper.parsers.lanacion import LaNacionParser


@pytest.fixture
def parser() -> LaNacionParser:
    """Create parser instance for tests."""
    return LaNacionParser()


class TestLaNacionParser:
    """Tests for LaNacionParser."""

    def test_parse_empty_html(self, parser: LaNacionParser) -> None:
        """Test parsing empty HTML returns empty list."""
        result = parser.parse("")
        assert result == []

    def test_parse_html_without_articles(self, parser: LaNacionParser) -> None:
        """Test parsing HTML with no article elements."""
        html = "<html><body><div>No articles here</div></body></html>"
        result = parser.parse(html)
        assert result == []

    def test_parse_single_article_with_h1(self, parser: LaNacionParser) -> None:
        """Test parsing HTML with a single featured article (h1 headline)."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/politica/test-article-nid123/">
                    <h1>Test Headline</h1>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Test Headline"
        assert result[0].url == "https://www.lanacion.com.ar/politica/test-article-nid123/"
        assert result[0].position == 1

    def test_parse_single_article_with_h2(self, parser: LaNacionParser) -> None:
        """Test parsing HTML with a regular article (h2 headline)."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/economia/test-nid456/">
                    <h2>Economic News Headline</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Economic News Headline"
        assert result[0].position == 1

    def test_parse_article_with_h1_headline_and_h2_summary(
        self, parser: LaNacionParser
    ) -> None:
        """Test parsing article with h1 headline and h2 summary."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/article/">
                    <h1>Main Headline</h1>
                    <h2>This is the summary text.</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Main Headline"
        assert result[0].summary == "This is the summary text."

    def test_parse_article_with_h2_headline_and_h3_summary(
        self, parser: LaNacionParser
    ) -> None:
        """Test parsing article with h2 headline and h3 summary."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/article/">
                    <h2>Regular Headline</h2>
                    <h3>Brief description of the article.</h3>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Regular Headline"
        assert result[0].summary == "Brief description of the article."

    def test_parse_multiple_articles(self, parser: LaNacionParser) -> None:
        """Test parsing HTML with multiple articles."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/first/">
                    <h2>First Article</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/second/">
                    <h2>Second Article</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/third/">
                    <h2>Third Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 3
        assert result[0].headline == "First Article"
        assert result[0].position == 1
        assert result[1].headline == "Second Article"
        assert result[1].position == 2
        assert result[2].headline == "Third Article"
        assert result[2].position == 3

    def test_parse_article_with_image(self, parser: LaNacionParser) -> None:
        """Test parsing article with image."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/article/">
                    <picture>
                        <img src="https://www.lanacion.com.ar/resizer/image.jpg" 
                             alt="Image description">
                    </picture>
                    <h2>Article with Image</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://www.lanacion.com.ar/resizer/image.jpg"

    def test_parse_deduplicates_by_url(self, parser: LaNacionParser) -> None:
        """Test that duplicate URLs are filtered out."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/same-article/">
                    <h2>First Instance</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/same-article/">
                    <h2>Second Instance</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/different-article/">
                    <h2>Different Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        # Should only have 2 unique articles
        assert len(result) == 2
        assert result[0].headline == "First Instance"
        assert result[0].position == 1
        assert result[1].headline == "Different Article"
        assert result[1].position == 2

    def test_parse_skips_card_without_headline(self, parser: LaNacionParser) -> None:
        """Test that cards without headlines are skipped."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/no-headline/">
                    <img src="image.jpg">
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/valid-article/">
                    <h2>Valid Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_skips_card_without_url(self, parser: LaNacionParser) -> None:
        """Test that cards without URLs are skipped."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <h2>No Link Article</h2>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/valid/">
                    <h2>Valid Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_handles_absolute_urls(self, parser: LaNacionParser) -> None:
        """Test parsing handles absolute URLs correctly."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="https://www.lanacion.com.ar/full/path/">
                    <h2>Absolute URL Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].url == "https://www.lanacion.com.ar/full/path/"

    def test_parse_skips_external_urls(self, parser: LaNacionParser) -> None:
        """Test that external URLs are rejected."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="https://other-site.com/article/">
                    <h2>External Article</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/valid-article/">
                    <h2>Valid Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        # External URL should be skipped
        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_accepts_lanacion_without_www(self, parser: LaNacionParser) -> None:
        """Test that lanacion.com.ar without www is accepted."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="https://lanacion.com.ar/article/">
                    <h2>No WWW Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].url == "https://lanacion.com.ar/article/"


class TestLaNacionParserHelpers:
    """Tests for LaNacionParser helper methods."""

    @pytest.fixture
    def parser(self) -> LaNacionParser:
        """Create parser instance for helper tests."""
        return LaNacionParser()

    def test_resolve_image_url_absolute(self, parser: LaNacionParser) -> None:
        """Test resolving absolute image URL."""
        url = "https://cdn.lanacion.com.ar/image.jpg"
        result = parser._resolve_image_url(url)
        assert result == url

    def test_resolve_image_url_relative(self, parser: LaNacionParser) -> None:
        """Test resolving relative image URL."""
        url = "/images/photo.jpg"
        result = parser._resolve_image_url(url)
        assert result == "https://www.lanacion.com.ar/images/photo.jpg"

    def test_resolve_image_url_protocol_relative(self, parser: LaNacionParser) -> None:
        """Test resolving protocol-relative image URL."""
        url = "//cdn.lanacion.com.ar/image.jpg"
        result = parser._resolve_image_url(url)
        assert result == "https://cdn.lanacion.com.ar/image.jpg"

    def test_resolve_article_url_relative(self, parser: LaNacionParser) -> None:
        """Test resolving relative article URL."""
        result = parser._resolve_article_url("/politica/article-nid123/")
        assert result == "https://www.lanacion.com.ar/politica/article-nid123/"

    def test_resolve_article_url_absolute(self, parser: LaNacionParser) -> None:
        """Test resolving absolute article URL."""
        result = parser._resolve_article_url("https://www.lanacion.com.ar/article/")
        assert result == "https://www.lanacion.com.ar/article/"

    def test_resolve_article_url_external_rejected(self, parser: LaNacionParser) -> None:
        """Test that external URLs return None."""
        result = parser._resolve_article_url("https://other-site.com/article/")
        assert result is None


class TestLaNacionParserRealHtml:
    """Integration tests using real HTML fixture from La Nacion."""

    @pytest.fixture
    def parser(self) -> LaNacionParser:
        """Create parser instance for tests."""
        return LaNacionParser()

    @pytest.fixture
    def lanacion_html(self) -> str:
        """Load real La Nacion HTML fixture."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "lanacion_sample.html"
        return fixture_path.read_text()

    def test_parse_real_html_extracts_articles(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test parsing real La Nacion HTML extracts expected articles."""
        result = parser.parse(lanacion_html)

        # Should extract significant number of articles
        assert len(result) >= 50  # La Nacion typically has 100+ articles

    def test_parse_real_html_first_article(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test first article from real HTML has expected data."""
        result = parser.parse(lanacion_html)

        first = result[0]
        assert first.headline  # Has headline
        assert len(first.headline) > 10  # Non-trivial headline
        assert first.url.startswith("https://www.lanacion.com.ar/")
        assert first.position == 1
        assert first.image_url is not None
        assert first.image_url.startswith("https://")

    def test_parse_real_html_all_have_headlines(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test all parsed articles have headlines."""
        result = parser.parse(lanacion_html)

        for article in result:
            assert article.headline
            assert len(article.headline) > 5

    def test_parse_real_html_all_have_urls(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test all parsed articles have valid URLs."""
        result = parser.parse(lanacion_html)

        for article in result:
            assert article.url
            assert article.url.startswith("https://")
            assert "lanacion.com.ar" in article.url

    def test_parse_real_html_no_duplicates(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test no duplicate URLs in parsed results."""
        result = parser.parse(lanacion_html)

        urls = [article.url for article in result]
        assert len(urls) == len(set(urls))

    def test_parse_real_html_positions_sequential(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test positions are sequential starting from 1."""
        result = parser.parse(lanacion_html)

        positions = [article.position for article in result]
        expected = list(range(1, len(result) + 1))
        assert positions == expected

    def test_parse_real_html_some_have_summaries(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test some articles have summaries."""
        result = parser.parse(lanacion_html)

        summaries = [a.summary for a in result if a.summary]
        # La Nacion has some articles with summaries
        assert len(summaries) >= 5

    def test_parse_real_html_most_have_images(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test most articles have images."""
        result = parser.parse(lanacion_html)

        with_images = [a for a in result if a.image_url]
        # Most La Nacion articles have images
        assert len(with_images) >= len(result) * 0.8
```

**File:** `tests/parsers/test_registry.py` (Updated)

Add test for La Nacion parser registration.

```python
"""Tests for parser registry."""

import pytest

from news_scraper.parsers import ParserNotFoundError, get_parser
from news_scraper.parsers.infobae import InfobaeParser
from news_scraper.parsers.lanacion import LaNacionParser


class TestGetParser:
    """Tests for get_parser function."""

    def test_get_infobae_parser(self) -> None:
        """Test getting Infobae parser returns instance."""
        parser = get_parser("infobae")
        assert isinstance(parser, InfobaeParser)

    def test_get_lanacion_parser(self) -> None:
        """Test getting La Nacion parser returns instance."""
        parser = get_parser("lanacion")
        assert isinstance(parser, LaNacionParser)

    def test_get_parser_case_insensitive(self) -> None:
        """Test parser lookup is case insensitive."""
        assert isinstance(get_parser("INFOBAE"), InfobaeParser)
        assert isinstance(get_parser("Infobae"), InfobaeParser)
        assert isinstance(get_parser("LANACION"), LaNacionParser)
        assert isinstance(get_parser("LaNacion"), LaNacionParser)

    def test_get_parser_unknown_source(self) -> None:
        """Test getting parser for unknown source raises error."""
        with pytest.raises(ParserNotFoundError) as exc_info:
            get_parser("unknown_source")

        assert exc_info.value.source_name == "unknown_source"
        assert "unknown_source" in str(exc_info.value)
```

### 5. Create HTML Fixture

**File:** `tests/fixtures/lanacion_sample.html`

Capture a snapshot of La Nacion's front page HTML during development.
This file should be created by running:

```bash
uv run python -c "
from news_scraper.browser import fetch_rendered_html

html = fetch_rendered_html('https://www.lanacion.com.ar/')
with open('tests/fixtures/lanacion_sample.html', 'w') as f:
    f.write(html)
print(f'Saved {len(html)} chars')
"
```

The fixture should contain enough articles to validate the parser works correctly with real HTML.

### 6. Update Project Structure Documentation

**File:** `docs/project-structure.md`

Add La Nacion parser:

```markdown
│   ├── parsers/          # Site-specific HTML parsers
│   │   ├── __init__.py   # Parser registry
│   │   ├── base.py       # Parser protocol + ParsedArticle dataclass
│   │   ├── infobae.py    # Infobae parser implementation
│   │   └── lanacion.py   # La Nacion parser implementation
```

## File Summary

**New files:**
- `alembic/versions/<revision>_seed_lanacion_source.py` - Migration to seed La Nacion source
- `src/news_scraper/parsers/lanacion.py` - La Nacion parser implementation
- `tests/parsers/test_lanacion.py` - La Nacion parser tests
- `tests/fixtures/lanacion_sample.html` - Real HTML fixture for integration tests

**Modified files:**
- `src/news_scraper/parsers/__init__.py` - Register La Nacion parser
- `tests/parsers/test_registry.py` - Add La Nacion parser registry tests
- `docs/project-structure.md` - Document La Nacion parser

## Acceptance Criteria

### Database
- [ ] La Nacion source seeded in database with name `lanacion`
- [ ] Source URL is `https://www.lanacion.com.ar`
- [ ] Source is enabled by default

### Parser
- [ ] `LaNacionParser` class created following Infobae pattern
- [ ] Finds articles by `<article class="ln-card">` elements
- [ ] Extracts headline from `<h1>` (featured) or `<h2>` (regular) elements
- [ ] Extracts summary from `<h2>` (when h1 exists) or `<h3>`
- [ ] Extracts URL from `<a class="ln-link">` href attribute
- [ ] Extracts image URL from `<img>` src attribute
- [ ] Resolves relative URLs to absolute using base URL
- [ ] Rejects external URLs (non-lanacion.com.ar domains)
- [ ] Deduplicates articles by URL (keeps first occurrence)
- [ ] Assigns sequential positions (1-based)
- [ ] Logs warning and continues if individual article fails to parse

### CLI Integration
- [ ] `news-scraper -s lanacion` works end-to-end
- [ ] Articles are persisted to database
- [ ] Output shows new/updated article counts

### Tests
- [ ] Unit tests cover all parser methods
- [ ] Integration tests pass with real HTML fixture
- [ ] Registry tests include La Nacion parser
- [ ] All tests pass (`uv run pytest`)

### Quality
- [ ] mypy passes with strict mode
- [ ] ruff passes
- [ ] pre-commit passes (`uv run pre-commit run --all-files`)
- [ ] Migration applies and rolls back cleanly

## Manual Verification

After implementation, verify using the browser agent (MCP cursor-ide-browser):

1. Navigate to https://www.lanacion.com.ar
2. Note visible headlines, images, and summaries for first 5 articles
3. Run `news-scraper -s lanacion`
4. Verify extracted data matches what's visible in the browser
5. Run again to verify updates work (no new articles if nothing changed)
6. Check database has articles with correct source_id

**Expected first articles (as of Jan 2026):**
1. "Análisis. El conflicto mundial se proyecta sobre Milei y Lula" (with summary)
2. "Los de arriba sabían". Investigan hasta dónde llegaban las complicidades..."
3. "Dato". Milei acusó a Paolo Rocca de conspirar..."

## Open Questions

None.

## Resolved Decisions

1. **Article container**: Use `<article class="ln-card">` - this is consistent across La Nacion's front page and identifies all article cards.

2. **Headline extraction**: Try `<h1>` first (featured articles), fall back to `<h2>` (regular articles). This matches La Nacion's HTML structure where featured articles use h1.

3. **Summary extraction**: When article has h1+h2, h2 is summary. When article has h2+h3, h3 is summary. When article has only h2, no summary.

4. **URL validation**: Accept both `www.lanacion.com.ar` and `lanacion.com.ar` domains to handle any URL variations.

5. **Image extraction**: Use `src` attribute from `<img>` elements. La Nacion serves images from CDN with absolute URLs.

## Future Work (Not in This Spec)

- Add more news sources (Clarin, etc.)
- Handle La Nacion's section pages (e.g., /politica/, /economia/)
- Extract author information
- Extract publication date
- Handle video articles differently
