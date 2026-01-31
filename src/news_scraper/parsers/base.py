"""Base classes for HTML parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, TypedDict

from bs4 import BeautifulSoup, Tag

from news_scraper.logging import get_logger


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


class ParsedArticleData(TypedDict, total=False):
    """Intermediate parsed data before mapping to ParsedArticle.

    Required keys:
        title: str
        url: str
    Optional keys:
        summary: str | None
        image_url: str | None
        published_at: datetime | None
        authors: list[str] | None
    """

    title: str
    url: str
    summary: str | None
    image_url: str | None
    published_at: datetime | None
    authors: list[str] | None


class BaseParser(ABC):
    """Base class for site parsers with shared workflow."""

    source: ClassVar[str] = ""
    base_url: ClassVar[str]
    allowed_hosts: ClassVar[set[str]]

    def parse(self, html: str) -> list[ParsedArticle]:
        """Parse HTML and extract articles with shared behavior."""
        log = get_logger()
        soup = self.build_soup(html)
        articles: list[ParsedArticle] = []
        seen: set[str] = set()
        position = 0

        for index, element in enumerate(self.iter_article_elements(soup), start=1):
            if not isinstance(element, Tag):
                continue

            parsed: ParsedArticleData | None = None
            try:
                parsed = self.parse_article_element(element)
                if not parsed:
                    continue

                title = (parsed.get("title") or "").strip()
                url = (parsed.get("url") or "").strip()
                if not title or not url:
                    continue

                dedupe_key = self.dedupe_key(url)
                if dedupe_key in seen:
                    continue

                summary = (parsed.get("summary") or "").strip() or None
                image_url = (parsed.get("image_url") or "").strip() or None

                position += 1
                articles.append(
                    ParsedArticle(
                        headline=title,
                        url=url,
                        position=position,
                        summary=summary,
                        image_url=image_url,
                    )
                )
                seen.add(dedupe_key)
            except Exception:
                log.exception(
                    "Failed to parse article element",
                    source=self.source,
                    url=(parsed or {}).get("url"),
                    position=index,
                )
                continue

        return articles

    def build_soup(self, html: str) -> BeautifulSoup:
        """Build BeautifulSoup instance (override for custom parsing)."""
        return BeautifulSoup(html, "lxml")

    def dedupe_key(self, url: str) -> str:
        """Return deduplication key for a normalized URL."""
        return url

    @abstractmethod
    def iter_article_elements(self, soup: BeautifulSoup) -> Iterable[Tag]:
        """Yield candidate article elements from the soup."""
        raise NotImplementedError

    @abstractmethod
    def parse_article_element(self, element: Tag) -> ParsedArticleData | None:
        """Parse a single article element into ParsedArticleData."""
        raise NotImplementedError
