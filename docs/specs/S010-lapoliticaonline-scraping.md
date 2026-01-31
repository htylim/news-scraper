# S010: Add La Política Online Scraping

Add La Política Online news source with parser implementation to scrape articles from the front page.

## Goal

Enable scraping from La Política Online (https://www.lapoliticaonline.com/):

```bash
news-scraper scrape lapoliticaonline
```

The command will:
1. Fetch rendered HTML from La Política Online front page
2. Parse HTML to extract articles using new `LaPoliticaOnlineParser`
3. Persist articles to database with deduplication
4. Print summary of new/updated articles to console

## Non-Goals

- No additional CLI argument validation beyond existing source lookup behavior
- No filtering of sponsored/advertorial cards yet
- No headline normalization/cleanup (keep raw text)
- No summary extraction (not present in HTML structure)

## Architecture

### Parser Strategy

Following the existing pattern (Infobae, La Nacion), create a site-specific parser that extends `BaseParser` and uses the `@register_parser` decorator.

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────────┐
│   scraper   │────>│ BaseParser  │<────│ LaPoliticaOnlineParser│
│             │     │             │     │                      │
└─────────────┘     └─────────────┘     └──────────────────────┘
                           △
                           │
                    ┌──────┴──────┐
                    │ InfobaeParser│
                    │ LaNacionParser│
                    └─────────────┘
```

### La Política Online HTML Structure (as of Jan 2026)

Based on browser inspection of https://www.lapoliticaonline.com/:

**Article Container:**
- Element: `<h2 class="title">` containing an `<a>` tag
- The `h2.title` elements identify individual articles
- ~95 articles found on front page
- Articles are nested within `div.noticia` containers (section containers), but the actual article identifier is `h2.title`

**URL:**
- Inside `h2.title`: `<a>` tag with `href` attribute
- URLs are relative (e.g., `/politica/furioso-por-la-revelacion-del-contrato-con-libra-milei-amenaza-con-el-cierre-de-clarin-5442/`)
- Base URL: `https://www.lapoliticaonline.com`
- Normalize URLs by stripping fragments and tracking params (e.g., `utm_*`)

**Headline:**
- Text content of `<a>` tag inside `<h2 class="title">`
- Headline text is the link text

**Summary:**
- Not present in the HTML structure inspected
- Optional field, will be None

**Image:**
- `<img>` element within the parent `div.noticia` container
- Use `src` attribute first, fall back to `data-src` for lazy loading
- Images may be relative paths (e.g., `/files/image/...`)
- Skip data URIs (base64 encoded images)

**Sample Article HTML:**

```html
<div class="piece news8 standard bordertop noticia item1high imageleft automaticfont">
  <div class="items">
    <div class="item">
      <div class="media oi">
        <div class="image">
          <a href="/politica/furioso-por-la-revelacion-del-contrato-con-libra-milei-amenaza-con-el-cierre-de-clarin-5442/">
            <picture>
              <img src="/files/image/269/269401/68efdddeea26e-horizontal-pieza-8-noticias_620_349!.jpg?s=..." />
            </picture>
          </a>
        </div>
      </div>
      <h2 class="title">
        <a href="/politica/furioso-por-la-revelacion-del-contrato-con-libra-milei-amenaza-con-el-cierre-de-clarin-5442/">
          Furioso por la revelación del contrato con Libra, Milei amenaza con el cierre de Clarín
        </a>
      </h2>
    </div>
  </div>
</div>
```

**Note on article identification:**
- Each `h2.title` element represents one article
- Multiple `h2.title` elements may be within a single `div.noticia` container (section grouping)
- The parser should iterate over all `h2.title` elements, not `div.noticia` containers

## Deliverables

### 1. Add La Política Online Source to Database

**File:** `alembic/versions/<revision>_seed_lapoliticaonline_source.py`

Create migration to seed La Política Online source. Make it idempotent so reruns in dev don't fail.

```python
"""seed lapoliticaonline source

Revision ID: <generated>
Revises: bcd78a54e570
Create Date: <generated>
"""

from collections.abc import Sequence

from alembic import op

revision: str = "<generated>"
down_revision: str | Sequence[str] | None = "bcd78a54e570"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Seed La Política Online source."""
    op.execute(
        """
        INSERT INTO sources (name, url, is_enabled, created_at, updated_at)
        SELECT
            'lapoliticaonline',
            'https://www.lapoliticaonline.com',
            1,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        WHERE NOT EXISTS (
            SELECT 1 FROM sources WHERE name = 'lapoliticaonline'
        )
        """
    )


def downgrade() -> None:
    """Remove La Política Online source."""
    op.execute("DELETE FROM sources WHERE name = 'lapoliticaonline'")
```

After creating migration, run: `uv run alembic upgrade head`

### 2. Create La Política Online Parser

**File:** `src/news_scraper/parsers/sites/lapoliticaonline.py`

Parser implementation for La Política Online's HTML structure.

```python
"""Parser for La Política Online news site."""

from __future__ import annotations

from typing import cast
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from news_scraper.parsers.base import BaseParser, ParsedArticleData
from news_scraper.parsers.registry import register_parser
from news_scraper.parsers.utils import first_srcset_url, resolve_url


@register_parser("lapoliticaonline")
class LaPoliticaOnlineParser(BaseParser):
    """Parser for La Política Online front page HTML."""

    base_url = "https://www.lapoliticaonline.com"
    allowed_hosts = {"www.lapoliticaonline.com", "lapoliticaonline.com"}

    def iter_article_elements(self, soup: BeautifulSoup) -> list[Tag]:
        """Find article headlines with h2.title class."""
        return cast(list[Tag], soup.find_all("h2", class_="title"))

    def parse_article_element(self, element: Tag) -> ParsedArticleData | None:
        """Extract article data from an h2.title element."""
        title = self._extract_headline(element)
        url = self._extract_url(element)
        if not title or not url:
            return None

        return {
            "title": title,
            "url": url,
            "summary": None,  # Not present in HTML structure
            "image_url": self._extract_image_url(element),
        }

    def _extract_headline(self, element: Tag) -> str | None:
        """Extract headline text from h2.title element."""
        link = element.find("a")
        if link:
            text: str = link.get_text(strip=True)
            if text:
                return text
        return None

    def _extract_url(self, element: Tag) -> str | None:
        """Extract article URL from element."""
        link = element.find("a")
        if link and isinstance(link, Tag):
            href = link.get("href")
            if href and isinstance(href, str):
                resolved = resolve_url(self.base_url, self.allowed_hosts, href)
                if resolved:
                    return resolved
        return None

    def _extract_image_url(self, element: Tag) -> str | None:
        """Extract image URL from article element.

        Images are in the parent div.noticia container.
        """
        # Find parent div.noticia container
        parent = element.find_parent("div", class_="noticia")
        if not parent:
            return None

        img = parent.find("img")
        if img and isinstance(img, Tag):
            # Try src first (most common), then data-src for lazy loading
            for attr in ("src", "data-src"):
                src = img.get(attr)
                if src and isinstance(src, str):
                    # Skip data URIs (base64 encoded images)
                    if src.startswith("data:"):
                        continue
                    return self._resolve_image_url(src)

            # Fall back to srcset/data-srcset for responsive images
            for attr in ("srcset", "data-srcset"):
                srcset = img.get(attr)
                if srcset and isinstance(srcset, str):
                    candidate = first_srcset_url(srcset)
                    if candidate and not candidate.startswith("data:"):
                        return self._resolve_image_url(candidate)

        return None

    def _resolve_image_url(self, url: str) -> str:
        """Resolve potentially relative image URL to absolute."""
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("/"):
            return urljoin(self.base_url, url)
        return url
```

### 3. Register La Política Online Parser

**File:** `src/news_scraper/parsers/__init__.py`

Add La Política Online parser to the module imports.

```python
"""Parsers module for extracting articles from news site HTML."""

from news_scraper.parsers.base import ParsedArticle
from news_scraper.parsers.registry import ParserNotFoundError, get_parser


def load_site_parsers() -> None:
    """Import site parsers to register them."""
    from news_scraper.parsers.sites import (
        infobae,
        lanacion,
        lapoliticaonline,  # noqa: F401
    )


__all__ = [
    "ParsedArticle",
    "get_parser",
    "load_site_parsers",
    "ParserNotFoundError",
]
```

### 4. Tests

**File:** `tests/parsers/sites/test_lapoliticaonline.py`

```python
"""Tests for La Política Online parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from news_scraper.parsers.sites.lapoliticaonline import LaPoliticaOnlineParser


@pytest.fixture
def parser() -> LaPoliticaOnlineParser:
    """Create parser instance for tests."""
    return LaPoliticaOnlineParser()


class TestLaPoliticaOnlineParser:
    """Tests for LaPoliticaOnlineParser."""

    def test_parse_empty_html(self, parser: LaPoliticaOnlineParser) -> None:
        """Test parsing empty HTML returns empty list."""
        result = parser.parse("")
        assert result == []

    def test_parse_html_without_articles(self, parser: LaPoliticaOnlineParser) -> None:
        """Test parsing HTML with no article elements."""
        html = "<html><body><div>No articles here</div></body></html>"
        result = parser.parse(html)
        assert result == []

    def test_parse_single_article(self, parser: LaPoliticaOnlineParser) -> None:
        """Test parsing HTML with a single article."""
        html = """
        <html>
        <body>
            <h2 class="title">
                <a href="/politica/test-article-123/">Test Headline</a>
            </h2>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Test Headline"
        assert (
            result[0].url
            == "https://www.lapoliticaonline.com/politica/test-article-123/"
        )
        assert result[0].position == 1

    def test_parse_multiple_articles(self, parser: LaPoliticaOnlineParser) -> None:
        """Test parsing HTML with multiple articles."""
        html = """
        <html>
        <body>
            <h2 class="title">
                <a href="/first/">First Article</a>
            </h2>
            <h2 class="title">
                <a href="/second/">Second Article</a>
            </h2>
            <h2 class="title">
                <a href="/third/">Third Article</a>
            </h2>
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

    def test_parse_article_with_image(self, parser: LaPoliticaOnlineParser) -> None:
        """Test parsing article with image."""
        html = """
        <html>
        <body>
            <div class="noticia">
                <img src="/files/image/test.jpg" />
                <h2 class="title">
                    <a href="/article/">Article with Image</a>
                </h2>
            </div>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert (
            result[0].image_url
            == "https://www.lapoliticaonline.com/files/image/test.jpg"
        )

    def test_parse_skips_data_uri_images(
        self, parser: LaPoliticaOnlineParser
    ) -> None:
        """Test that data URI images are skipped."""
        html = """
        <html>
        <body>
            <div class="noticia">
                <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..." />
                <h2 class="title">
                    <a href="/article/">Article</a>
                </h2>
            </div>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url is None

    def test_parse_deduplicates_by_url(
        self, parser: LaPoliticaOnlineParser
    ) -> None:
        """Test that duplicate URLs are filtered out."""
        html = """
        <html>
        <body>
            <h2 class="title">
                <a href="/same-article/">First Instance</a>
            </h2>
            <h2 class="title">
                <a href="/same-article/">Second Instance</a>
            </h2>
            <h2 class="title">
                <a href="/different-article/">Different Article</a>
            </h2>
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

    def test_parse_skips_title_without_link(
        self, parser: LaPoliticaOnlineParser
    ) -> None:
        """Test that titles without links are skipped."""
        html = """
        <html>
        <body>
            <h2 class="title">No Link Title</h2>
            <h2 class="title">
                <a href="/valid-article/">Valid Article</a>
            </h2>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_handles_absolute_urls(
        self, parser: LaPoliticaOnlineParser
    ) -> None:
        """Test parsing handles absolute URLs correctly."""
        html = """
        <html>
        <body>
            <h2 class="title">
                <a href="https://www.lapoliticaonline.com/full/path/">
                    Absolute URL Article
                </a>
            </h2>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert (
            result[0].url == "https://www.lapoliticaonline.com/full/path/"
        )

    def test_parse_skips_external_urls(
        self, parser: LaPoliticaOnlineParser
    ) -> None:
        """Test that external URLs are rejected."""
        html = """
        <html>
        <body>
            <h2 class="title">
                <a href="https://other-site.com/article/">External Article</a>
            </h2>
            <h2 class="title">
                <a href="/valid-article/">Valid Article</a>
            </h2>
        </body>
        </html>
        """
        result = parser.parse(html)

        # External URL should be skipped
        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_accepts_lapoliticaonline_without_www(
        self, parser: LaPoliticaOnlineParser
    ) -> None:
        """Test that lapoliticaonline.com without www is accepted."""
        html = """
        <html>
        <body>
            <h2 class="title">
                <a href="https://lapoliticaonline.com/article/">No WWW Article</a>
            </h2>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].url == "https://lapoliticaonline.com/article/"


class TestLaPoliticaOnlineParserHelpers:
    """Tests for LaPoliticaOnlineParser helper methods."""

    @pytest.fixture
    def parser(self) -> LaPoliticaOnlineParser:
        """Create parser instance for helper tests."""
        return LaPoliticaOnlineParser()

    def test_resolve_image_url_absolute(
        self, parser: LaPoliticaOnlineParser
    ) -> None:
        """Test resolving absolute image URL."""
        url = "https://cdn.lapoliticaonline.com/image.jpg"
        result = parser._resolve_image_url(url)
        assert result == url

    def test_resolve_image_url_relative(
        self, parser: LaPoliticaOnlineParser
    ) -> None:
        """Test resolving relative image URL."""
        url = "/files/image/photo.jpg"
        result = parser._resolve_image_url(url)
        assert (
            result == "https://www.lapoliticaonline.com/files/image/photo.jpg"
        )

    def test_resolve_image_url_protocol_relative(
        self, parser: LaPoliticaOnlineParser
    ) -> None:
        """Test resolving protocol-relative image URL."""
        url = "//cdn.lapoliticaonline.com/image.jpg"
        result = parser._resolve_image_url(url)
        assert result == "https://cdn.lapoliticaonline.com/image.jpg"


class TestLaPoliticaOnlineParserRealHtml:
    """Integration tests using real HTML fixture from La Política Online."""

    # Fixture-based expectations: update these constants only when regenerating
    # the fixture. This keeps tests deterministic and avoids brittle ratio checks.

    EXPECTED_ARTICLE_COUNT = 0  # Update to match fixture snapshot
    EXPECTED_WITH_IMAGES_COUNT = 0  # Update to match fixture snapshot

    @pytest.fixture
    def parser(self) -> LaPoliticaOnlineParser:
        """Create parser instance for tests."""
        return LaPoliticaOnlineParser()

    @pytest.fixture
    def lapoliticaonline_html(self) -> str:
        """Load real La Política Online HTML fixture."""
        fixture_path = (
            Path(__file__).parent.parent.parent
            / "fixtures"
            / "lapoliticaonline_sample.html"
        )
        return fixture_path.read_text(encoding="utf-8")

    def test_parse_real_html_extracts_articles(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test parsing real La Política Online HTML extracts expected articles."""
        result = parser.parse(lapoliticaonline_html)

        # Fixture-based expectation: update constants when fixture changes
        assert len(result) == self.EXPECTED_ARTICLE_COUNT

    def test_parse_real_html_first_article(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test first article from real HTML has expected data."""
        result = parser.parse(lapoliticaonline_html)

        if not result:
            pytest.skip("No articles found in fixture")

        first = result[0]
        assert first.headline  # Has headline
        assert len(first.headline) > 10  # Non-trivial headline
        assert first.url.startswith("https://www.lapoliticaonline.com/")
        assert first.position == 1

    def test_parse_real_html_all_have_headlines(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test all parsed articles have headlines."""
        result = parser.parse(lapoliticaonline_html)

        for article in result:
            assert article.headline
            assert len(article.headline) > 5

    def test_parse_real_html_all_have_urls(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test all parsed articles have valid URLs."""
        result = parser.parse(lapoliticaonline_html)

        for article in result:
            assert article.url
            assert article.url.startswith("https://")
            assert "lapoliticaonline.com" in article.url

    def test_parse_real_html_no_duplicates(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test no duplicate URLs in parsed results."""
        result = parser.parse(lapoliticaonline_html)

        urls = [article.url for article in result]
        assert len(urls) == len(set(urls))

    def test_parse_real_html_positions_sequential(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test positions are sequential starting from 1."""
        result = parser.parse(lapoliticaonline_html)

        positions = [article.position for article in result]
        expected = list(range(1, len(result) + 1))
        assert positions == expected

    def test_parse_real_html_most_have_images(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test most articles have images."""
        result = parser.parse(lapoliticaonline_html)

        with_images = [a for a in result if a.image_url]
        assert len(with_images) == self.EXPECTED_WITH_IMAGES_COUNT
```

**File:** `tests/parsers/test_registry.py` (Updated)

Add test for La Política Online parser registration.

```python
"""Tests for parser registry."""

import pytest

from news_scraper.parsers import ParserNotFoundError, get_parser
from news_scraper.parsers.sites.infobae import InfobaeParser
from news_scraper.parsers.sites.lanacion import LaNacionParser
from news_scraper.parsers.sites.lapoliticaonline import LaPoliticaOnlineParser


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

    def test_get_lapoliticaonline_parser(self) -> None:
        """Test getting La Política Online parser returns instance."""
        parser = get_parser("lapoliticaonline")
        assert isinstance(parser, LaPoliticaOnlineParser)

    def test_get_parser_case_insensitive(self) -> None:
        """Test parser lookup is case insensitive."""
        assert isinstance(get_parser("INFOBAE"), InfobaeParser)
        assert isinstance(get_parser("Infobae"), InfobaeParser)
        assert isinstance(get_parser("LANACION"), LaNacionParser)
        assert isinstance(get_parser("LaNacion"), LaNacionParser)
        assert isinstance(
            get_parser("LAPOLITICAONLINE"), LaPoliticaOnlineParser
        )
        assert isinstance(
            get_parser("LaPoliticaOnline"), LaPoliticaOnlineParser
        )

    def test_get_parser_unknown_source(self) -> None:
        """Test getting parser for unknown source raises error."""
        with pytest.raises(ParserNotFoundError) as exc_info:
            get_parser("unknown_source")

        assert exc_info.value.source_name == "unknown_source"
        assert "unknown_source" in str(exc_info.value)
```

### 5. HTML Fixture

**File:** `tests/fixtures/lapoliticaonline_sample.html`

Already created by fetching the page HTML. This file contains a snapshot of La Política Online's front page HTML for integration tests.

The fixture should contain enough articles to validate the parser works correctly with real HTML.
Keep the fixture stable and avoid regenerating unless the site changes significantly.

### 6. Update Project Structure Documentation

**File:** `docs/project-structure.md`

Add La Política Online parser:

```markdown
│   ├── parsers/                    # Site-specific HTML parsers
│   │   ├── __init__.py             # Parser registry
│   │   ├── base.py                 # BaseParser class + ParsedArticle dataclass
│   │   ├── registry.py             # Parser registration decorator
│   │   ├── utils.py                # Shared parser utilities
│   │   └── sites/                  # Site-specific parsers
│   │       ├── __init__.py         # Site parser imports
│   │       ├── infobae.py          # Infobae parser implementation
│   │       ├── lanacion.py         # La Nacion parser implementation
│   │       └── lapoliticaonline.py # La Política Online parser implementation
```

## File Summary

**New files:**
- `alembic/versions/<revision>_seed_lapoliticaonline_source.py` - Migration to seed La Política Online source
- `src/news_scraper/parsers/sites/lapoliticaonline.py` - La Política Online parser implementation
- `tests/parsers/sites/test_lapoliticaonline.py` - La Política Online parser tests
- `tests/fixtures/lapoliticaonline_sample.html` - Real HTML fixture for integration tests

**Modified files:**
- `src/news_scraper/parsers/__init__.py` - Import La Política Online parser module
- `tests/parsers/test_registry.py` - Add La Política Online parser registry tests
- `docs/project-structure.md` - Document La Política Online parser

## Acceptance Criteria

### Database
- [ ] La Política Online source seeded in database with name `lapoliticaonline`
- [ ] Source URL is `https://www.lapoliticaonline.com`
- [ ] Source is enabled by default

### Parser
- [ ] `LaPoliticaOnlineParser` class created following Infobae/La Nacion pattern
- [ ] Finds articles by `<h2 class="title">` elements
- [ ] Extracts headline from `<a>` tag text inside `h2.title`
- [ ] Extracts URL from `<a>` tag `href` attribute inside `h2.title`
- [ ] Normalizes URLs (strip fragments/tracking params) before deduplication
- [ ] Extracts image URL from `<img>` in parent `div.noticia` container
- [ ] Resolves relative image URLs to absolute using base URL
- [ ] Skips data URI images (base64 encoded)
- [ ] Rejects external URLs (non-lapoliticaonline.com domains)
- [ ] Deduplicates articles by URL (keeps first occurrence)
- [ ] Assigns sequential positions (1-based)
- [ ] Logs warning (with stack trace) and continues if individual article fails to parse

### CLI Integration
- [ ] `news-scraper scrape lapoliticaonline` works end-to-end
- [ ] Articles are persisted to database
- [ ] Output shows new/updated article counts

### Tests
- [ ] Unit tests cover all parser methods
- [ ] Integration tests pass with real HTML fixture
- [ ] Registry tests include La Política Online parser
- [ ] All tests pass (`uv run pytest`)

### Quality
- [ ] mypy passes with strict mode
- [ ] ruff passes
- [ ] pre-commit passes (`uv run pre-commit run --all-files`)
- [ ] Migration applies and rolls back cleanly

## Manual Verification

After implementation, verify using the browser agent (MCP cursor-ide-browser):

1. Navigate to https://www.lapoliticaonline.com
2. Note visible headlines and images for first 5 articles
3. Run `news-scraper scrape lapoliticaonline`
4. Verify extracted data matches what's visible in the browser
5. Run again to verify updates work (no new articles if nothing changed)
6. Check database has articles with correct source_id

**Expected first articles (as of Jan 2026):**
1. "Furioso por la revelación del contrato con Libra, Milei amenaza con el cierre de Clarín"
2. "Lule Menem le quiere sacar el partido a Villaverde en Río Negro"
3. "La Justicia le pone un límite a la política de Pullaro de aislar a presos de alto riesgo"

## Open Questions

None.

## Resolved Decisions

1. **Article container**: Use `<h2 class="title">` - this identifies individual articles on La Política Online's front page. Multiple `h2.title` elements may be within `div.noticia` containers (section groupings), but each `h2.title` represents one article.

2. **Headline extraction**: Extract text from `<a>` tag inside `<h2 class="title">`. This is the article headline.

3. **Summary extraction**: Not present in HTML structure - will be None for all articles.

4. **URL validation**: Accept both `www.lapoliticaonline.com` and `lapoliticaonline.com` domains to handle any URL variations.

5. **Image extraction**: Images are in parent `div.noticia` container. Prefer `src` attribute, fall back to `data-src` for lazy loading. Skip data URIs.

6. **Headline text**: Keep headline text as-is (no normalization).

7. **Sponsored/advertorial cards**: Do not filter them yet; treat any `h2.title` as a candidate article.

## Future Work (Not in This Spec)

- Add more news sources
- Handle La Política Online's section pages (e.g., /politica/, /economia/)
- Extract author information
- Extract publication date
- Handle video articles differently
- Add summary extraction if structure changes
