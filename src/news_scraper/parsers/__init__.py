"""Parsers module for extracting articles from news site HTML."""

from news_scraper.parsers.base import ParsedArticle
from news_scraper.parsers.registry import ParserNotFoundError, get_parser


def load_site_parsers() -> None:
    """Import site parsers to register them."""
    from news_scraper.parsers.sites import infobae, lanacion  # noqa: F401


__all__ = [
    "ParsedArticle",
    "get_parser",
    "load_site_parsers",
    "ParserNotFoundError",
]
