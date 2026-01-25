"""Scraper module for news sources."""

from news_scraper.db.models import Source


def scrape(source: Source) -> None:
    """Scrape news from the given source.

    Args:
        source: The source to scrape.
    """
    print(f"Scraping {source.name}")
