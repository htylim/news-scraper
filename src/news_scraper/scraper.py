"""Scraper module for news sources."""

from news_scraper.browser import BrowserError, fetch_rendered_html
from news_scraper.db.models import Source
from news_scraper.logging import get_logger


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


def scrape(source: Source) -> None:
    """Scrape news from the given source.

    Fetches the source URL using a headless browser and prints
    the rendered HTML to stdout.

    Args:
        source: The source to scrape.

    Raises:
        ScraperError: If fetching the page fails.
    """
    log = get_logger()
    log.info("Fetching page with headless browser", url=source.url)

    try:
        html = fetch_rendered_html(source.url)
    except BrowserError as e:
        log.error("Failed to fetch page", url=source.url, error=e.message)
        raise ScraperError(e.message, source.name) from e

    log.info("Page fetched successfully", html_length=len(html))
    print(html)
