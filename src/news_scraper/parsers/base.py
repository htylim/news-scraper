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
        position: 1-based position on the page (1 = top/most prominent).
        summary: Brief description or subheadline. None if not available.
        image_url: URL of the associated image. None if not available.
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
