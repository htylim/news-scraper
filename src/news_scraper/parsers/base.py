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
