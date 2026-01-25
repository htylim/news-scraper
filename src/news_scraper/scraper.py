"""Scraper module for news sources."""

from rich.console import Console
from rich.markup import escape

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
    # Escape Rich markup in user-provided content to prevent corruption
    headline = escape(article.headline)
    url = escape(article.url)

    lines = [
        f"[{index}] {headline}",
        f"    URL: {url}",
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
