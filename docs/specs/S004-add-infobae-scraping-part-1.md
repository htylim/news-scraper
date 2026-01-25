# S004: Add Infobae Scraping - Part 1 (Headless Browser Rendering)

Use Playwright to render JavaScript-heavy pages and print raw HTML to console.

## Goal

Enable running the scraper for "infobae" source with headless browser rendering:

```bash
news-scraper -s infobae
```

The command will:
1. Lookup "infobae" source in database (existing behavior from S003)
2. Launch headless Chrome via Playwright
3. Navigate to source URL and wait for page to render
4. Print the full rendered HTML to stdout
5. Close the browser

This is Part 1 - fetching and printing HTML only. Parsing comes in a later spec.

## Why Playwright?

Infobae (and many modern news sites) renders content via JavaScript. A simple HTTP request won't get the full article content. Playwright launches a real browser to execute JavaScript and render the final DOM.

## Deliverables

### 1. Add Playwright Dependency

**File:** `pyproject.toml`

Add playwright to runtime dependencies:

```toml
dependencies = [
    "typer",
    "rich",
    "structlog",
    "sqlalchemy>=2.0.46",
    "alembic>=1.18.1",
    "playwright>=1.57.0",
]
```

**Note:** Playwright 1.57.0 (Dec 2025) includes:
- Python 3.12 support
- Built-in type annotations (`py.typed`) - no separate stubs needed for mypy
- Chrome for Testing builds

### 2. Browser Module

**File:** `src/news_scraper/browser.py`

New module encapsulating Playwright browser operations.

```python
"""Browser module for headless page rendering."""

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

# Realistic Chrome User-Agent to avoid bot detection
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class BrowserError(Exception):
    """Exception raised when browser operations fail."""

    def __init__(self, message: str, url: str) -> None:
        """Initialize BrowserError.

        Args:
            message: Error description.
            url: The URL that failed to load.
        """
        self.message = message
        self.url = url
        super().__init__(message)


def fetch_rendered_html(url: str, timeout: int = 30000) -> str:
    """Fetch fully-rendered HTML from a URL using headless browser.

    Launches headless Chrome, navigates to the URL, waits for the page
    to load, and returns the rendered HTML.

    Args:
        url: The URL to fetch.
        timeout: Navigation timeout in milliseconds. Defaults to 30000 (30s).

    Returns:
        The fully-rendered HTML content of the page.

    Raises:
        BrowserError: If browser launch or navigation fails.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, channel="chrome")
            try:
                context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
                page = context.new_page()
                page.goto(url, timeout=timeout, wait_until="networkidle")
                return page.content()
            finally:
                browser.close()
    except PlaywrightError as e:
        raise BrowserError(str(e), url) from e
```

Design notes:
- Uses sync API (async not needed for CLI)
- `channel="chrome"` uses locally installed Chrome (no browser download needed)
- `wait_until="networkidle"` waits for JavaScript to finish loading
- `try/finally` ensures browser cleanup even on navigation error
- Timeout configurable, defaults to 30 seconds
- Custom `BrowserError` wraps Playwright errors with URL context
- Realistic Chrome User-Agent avoids bot detection on news sites
- Future: containerized version will use bundled Playwright browsers

### 3. Update Scraper Module

**File:** `src/news_scraper/scraper.py`

Replace placeholder with browser-based fetching.

```python
"""Scraper module for news sources."""

from news_scraper.browser import fetch_rendered_html
from news_scraper.db.models import Source
from news_scraper.logging import get_logger


def scrape(source: Source) -> None:
    """Scrape news from the given source.

    Fetches the source URL using a headless browser and prints
    the rendered HTML to stdout.

    Args:
        source: The source to scrape.
    """
    log = get_logger()
    log.info("Fetching page with headless browser", url=source.url)

    html = fetch_rendered_html(source.url)

    log.info("Page fetched successfully", html_length=len(html))
    print(html)
```

### 4. Seed Infobae Source (Migration)

**File:** `alembic/versions/<revision>_seed_infobae_source.py`

Generate with: `uv run alembic revision -m "seed infobae source"`

```python
"""seed infobae source

Revision ID: <generated>
Revises: 4fc40fb00ec0
Create Date: <generated>

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "<generated>"
down_revision: str | Sequence[str] | None = "4fc40fb00ec0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Seed infobae source."""
    op.execute(
        """
        INSERT INTO sources (name, url, is_enabled, created_at, updated_at)
        VALUES (
            'infobae',
            'https://www.infobae.com',
            1,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        """
    )


def downgrade() -> None:
    """Remove infobae source."""
    op.execute("DELETE FROM sources WHERE name = 'infobae'")
```

After creating migration, run: `uv run alembic upgrade head`

### 5. Update Libraries Documentation

**File:** `docs/libraries.md`

Add playwright to runtime dependencies:

```markdown
## Runtime

- **typer** - CLI framework
- **rich** - Terminal output formatting
- **structlog** - Structured logging
- **sqlalchemy** - ORM with native type hints (2.0+)
- **alembic** - Database migrations
- **playwright** - Headless browser automation for JS-rendered pages
```

### 6. Tests

**File:** `tests/test_browser.py`

```python
"""Tests for the browser module."""

from unittest.mock import MagicMock, patch

import pytest

from news_scraper.browser import BrowserError, fetch_rendered_html


class TestFetchRenderedHtml:
    """Tests for fetch_rendered_html function."""

    def test_returns_page_content(self) -> None:
        """Test that page HTML content is returned."""
        mock_html = "<html><body>Test content</body></html>"

        with patch("news_scraper.browser.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = mock_html

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = (
                mock_browser
            )
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            result = fetch_rendered_html("https://example.com")

            assert result == mock_html
            mock_page.goto.assert_called_once_with(
                "https://example.com", timeout=30000, wait_until="networkidle"
            )

    def test_browser_closed_on_success(self) -> None:
        """Test browser is closed after successful fetch."""
        with patch("news_scraper.browser.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = "<html></html>"

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = (
                mock_browser
            )
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            fetch_rendered_html("https://example.com")

            mock_browser.close.assert_called_once()

    def test_browser_closed_on_navigation_error(self) -> None:
        """Test browser is closed even when navigation fails."""
        with patch("news_scraper.browser.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()

            # Import PlaywrightError to raise it
            from playwright.sync_api import Error as PlaywrightError

            mock_page.goto.side_effect = PlaywrightError("Navigation failed")

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = (
                mock_browser
            )
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            with pytest.raises(BrowserError, match="Navigation failed"):
                fetch_rendered_html("https://example.com")

            mock_browser.close.assert_called_once()

    def test_custom_timeout(self) -> None:
        """Test custom timeout is passed to page.goto."""
        with patch("news_scraper.browser.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = "<html></html>"

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = (
                mock_browser
            )
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            fetch_rendered_html("https://example.com", timeout=60000)

            mock_page.goto.assert_called_once_with(
                "https://example.com", timeout=60000, wait_until="networkidle"
            )

    def test_launches_chrome_headless(self) -> None:
        """Test browser launches Chrome in headless mode."""
        with patch("news_scraper.browser.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = "<html></html>"

            mock_chromium = mock_pw.return_value.__enter__.return_value.chromium
            mock_chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            fetch_rendered_html("https://example.com")

            mock_chromium.launch.assert_called_once_with(headless=True, channel="chrome")

    def test_sets_custom_user_agent(self) -> None:
        """Test browser context is created with custom user agent."""
        with patch("news_scraper.browser.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = "<html></html>"

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = (
                mock_browser
            )
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            fetch_rendered_html("https://example.com")

            # Verify new_context was called with a user_agent parameter
            mock_browser.new_context.assert_called_once()
            call_kwargs = mock_browser.new_context.call_args.kwargs
            assert "user_agent" in call_kwargs
            assert "Mozilla/5.0" in call_kwargs["user_agent"]
```

**File:** `tests/test_scraper.py`

Replace existing tests to mock browser module.

```python
"""Tests for the scraper module."""

from unittest.mock import patch

import pytest

from news_scraper.db.models import Source
from news_scraper.scraper import scrape


class TestScrape:
    """Tests for the scrape function."""

    def test_scrape_prints_html(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test scrape prints rendered HTML to stdout."""
        source = Source(name="testsource", url="https://test.com")
        mock_html = "<html><body>Test content</body></html>"

        with patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch:
            mock_fetch.return_value = mock_html

            scrape(source)

            mock_fetch.assert_called_once_with("https://test.com")
            captured = capsys.readouterr()
            assert mock_html in captured.out

    def test_scrape_uses_source_url(self) -> None:
        """Test scrape passes source URL to fetch function."""
        source = Source(name="infobae", url="https://www.infobae.com")

        with patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch:
            mock_fetch.return_value = "<html></html>"

            scrape(source)

            mock_fetch.assert_called_once_with("https://www.infobae.com")

    def test_scrape_different_sources(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test scrape works with different sources."""
        with patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch:
            source1 = Source(name="infobae", url="https://infobae.com")
            mock_fetch.return_value = "<html>Source 1</html>"
            scrape(source1)
            captured1 = capsys.readouterr()
            assert "<html>Source 1</html>" in captured1.out

            source2 = Source(name="clarin", url="https://clarin.com")
            mock_fetch.return_value = "<html>Source 2</html>"
            scrape(source2)
            captured2 = capsys.readouterr()
            assert "<html>Source 2</html>" in captured2.out
```

### 7. Prerequisites

Playwright uses the locally installed Chrome browser via `channel="chrome"`. Chrome must be installed on the development machine.

**Note:** Future containerized deployment will bundle Playwright browsers directly.

## File Summary

**New files:**
- `src/news_scraper/browser.py` - Playwright browser operations
- `tests/test_browser.py` - Browser module tests
- `alembic/versions/<revision>_seed_infobae_source.py` - Seed infobae source

**Modified files:**
- `pyproject.toml` - Add playwright dependency
- `src/news_scraper/scraper.py` - Use browser module, print HTML
- `tests/test_scraper.py` - Update tests to mock browser
- `docs/libraries.md` - Document playwright

## Acceptance Criteria

### CLI Functionality
- [ ] `news-scraper -s infobae` fetches https://www.infobae.com with headless browser
- [ ] Rendered HTML is printed to stdout
- [ ] Browser is properly closed after fetch (success or failure)
- [ ] Existing CLI flags (`--verbose`, `--version`, `--help`) still work

### Browser Module
- [ ] `fetch_rendered_html()` returns page HTML as string
- [ ] Uses local Chrome via `channel="chrome"` (no browser download required)
- [ ] Runs in headless mode
- [ ] Waits for network idle before returning content
- [ ] Configurable timeout (default 30s)
- [ ] Browser cleanup on error (finally block)
- [ ] Custom `BrowserError` exception wraps Playwright errors with URL context
- [ ] Realistic Chrome User-Agent set via browser context to avoid bot detection

### Data
- [ ] Migration seeds "infobae" source with URL https://www.infobae.com
- [ ] Migration is reversible (downgrade removes source)

### Quality
- [ ] All tests pass (`uv run pytest`)
- [ ] mypy passes with strict mode
- [ ] ruff passes
- [ ] pre-commit passes (`uv run pre-commit run --all-files`)

## Open Questions

1. **Timeout value** - Is 30 seconds appropriate for news sites? May need tuning based on testing.

## Resolved Decisions

1. **Error handling** - Navigation errors are wrapped in a custom `BrowserError` exception that includes both the error message and the URL that failed. This provides better context for debugging while allowing callers to handle errors appropriately.

2. **User-Agent** - A realistic Chrome User-Agent is set via `DEFAULT_USER_AGENT` constant to avoid bot detection. The implementation uses `browser.new_context(user_agent=...)` to apply it. The chosen UA mimics Chrome 120 on macOS.

## Future Work (Not in This Spec)

- Parse HTML to extract article data
- Handle pagination / article listing
- Rate limiting / polite scraping delays
- Screenshot capture for debugging
- Cookie consent / popup handling
- Containerize scraper with Docker (Playwright image with bundled browsers)
