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
