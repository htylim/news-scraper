"""Parser registry and lookup."""

from __future__ import annotations

from collections.abc import Callable

from news_scraper.parsers.base import BaseParser


class ParserNotFoundError(Exception):
    """Raised when no parser is registered for a source."""

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name
        super().__init__(f"No parser registered for source: {source_name}")


_PARSERS: dict[str, type[BaseParser]] = {}


def register_parser(source_name: str) -> Callable[[type[BaseParser]], type[BaseParser]]:
    """Decorator to register a parser class for a source."""

    def decorator(parser_cls: type[BaseParser]) -> type[BaseParser]:
        key = source_name.lower()
        if key in _PARSERS:
            raise ValueError(f"Parser already registered for source: {source_name}")
        parser_cls.source = source_name
        _PARSERS[key] = parser_cls
        return parser_cls

    return decorator


def get_parser(source_name: str) -> BaseParser:
    """Get a parser instance for a source."""
    parser_cls = _PARSERS.get(source_name.lower())
    if parser_cls is None:
        raise ParserNotFoundError(source_name)
    return parser_cls()
