"""Tests for parser base classes."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup, Tag

from news_scraper.parsers.base import BaseParser, ParsedArticle, ParsedArticleData
from news_scraper.parsers.utils import first_srcset_url, resolve_url


class TestParsedArticle:
    """Tests for ParsedArticle dataclass."""

    def test_article_with_all_fields(self) -> None:
        """Test creating article with all fields."""
        article = ParsedArticle(
            headline="Test Headline",
            url="https://example.com/article",
            position=1,
            summary="Test summary",
            image_url="https://example.com/image.jpg",
        )

        assert article.headline == "Test Headline"
        assert article.url == "https://example.com/article"
        assert article.position == 1
        assert article.summary == "Test summary"
        assert article.image_url == "https://example.com/image.jpg"

    def test_article_with_required_fields_only(self) -> None:
        """Test creating article with only required fields."""
        article = ParsedArticle(
            headline="Test Headline",
            url="https://example.com/article",
            position=5,
        )

        assert article.headline == "Test Headline"
        assert article.url == "https://example.com/article"
        assert article.position == 5
        assert article.summary is None
        assert article.image_url is None

    def test_article_is_frozen(self) -> None:
        """Test that ParsedArticle is immutable."""
        article = ParsedArticle(headline="Test", url="https://example.com", position=1)

        with pytest.raises(AttributeError):
            article.headline = "Modified"  # type: ignore[misc]

    def test_article_is_hashable(self) -> None:
        """Test that ParsedArticle can be used in sets."""
        article1 = ParsedArticle(headline="Test", url="https://example.com", position=1)
        article2 = ParsedArticle(headline="Test", url="https://example.com", position=1)

        article_set = {article1, article2}
        assert len(article_set) == 1


class _StubParser(BaseParser):
    """Minimal parser for BaseParser behavior tests."""

    source = "stub"
    base_url = "https://example.com"
    allowed_hosts = {"example.com"}

    def iter_article_elements(self, soup: BeautifulSoup) -> list[Tag]:
        return cast(list[Tag], soup.find_all("article"))

    def parse_article_element(self, element: Tag) -> ParsedArticleData | None:
        if element.get("data-error") == "1":
            raise RuntimeError("Simulated error")

        title = element.get("data-title")
        href = element.get("data-href")
        if not title or not href:
            return None

        url = resolve_url(self.base_url, self.allowed_hosts, href)
        if not url:
            return None

        return {
            "title": title,
            "url": url,
            "summary": element.get("data-summary"),
        }


class TestBaseParser:
    """Tests for BaseParser workflow."""

    def test_parse_dedupes_on_normalized_url(self) -> None:
        """Duplicate URLs after normalization keep first element."""
        html = """
        <article data-title="First" data-href="/article/?utm=1"></article>
        <article data-title="Second" data-href="/article/?utm=2"></article>
        """
        parser = _StubParser()
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "First"

    def test_parse_assigns_positions_to_valid_elements(self) -> None:
        """Positions are sequential for accepted elements."""
        html = """
        <article data-title="One" data-href="/one/"></article>
        <article data-href="/missing-title/"></article>
        <article data-title="Two" data-href="/two/"></article>
        """
        parser = _StubParser()
        result = parser.parse(html)

        assert [article.position for article in result] == [1, 2]
        assert [article.headline for article in result] == ["One", "Two"]

    def test_parse_logs_and_continues_on_error(self) -> None:
        """Exceptions are logged and skipped without stopping."""
        html = """
        <article data-error="1" data-title="Bad" data-href="/bad/"></article>
        <article data-title="Good" data-href="/good/"></article>
        """
        parser = _StubParser()

        with patch("news_scraper.parsers.base.get_logger") as mock_get_logger:
            logger = MagicMock()
            mock_get_logger.return_value = logger
            result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Good"
        assert logger.exception.call_count == 1
        _, kwargs = logger.exception.call_args
        assert kwargs["source"] == "stub"
        assert kwargs["position"] == 1


class TestResolveUrl:
    """Tests for resolve_url helper."""

    def test_rejects_fragment_only(self) -> None:
        """Fragment-only URLs are rejected."""
        assert resolve_url("https://example.com", {"example.com"}, "#section") is None

    def test_rejects_non_http_scheme(self) -> None:
        """Non-http(s) schemes are rejected."""
        href = "mailto:test@example.com"
        assert resolve_url("https://example.com", {"example.com"}, href) is None

    def test_rejects_root_path(self) -> None:
        """Root paths are rejected."""
        assert resolve_url("https://example.com", {"example.com"}, "/") is None

    def test_allows_subdomains(self) -> None:
        """Subdomains of allowed hosts are accepted."""
        url = resolve_url(
            "https://example.com",
            {"example.com"},
            "https://news.example.com/path/?q=1#frag",
        )
        assert url == "https://news.example.com/path/"


class TestFirstSrcsetUrl:
    """Tests for first_srcset_url helper."""

    def test_blank_srcset_returns_none(self) -> None:
        """Blank srcset returns None."""
        assert first_srcset_url("   ") is None

    def test_returns_first_entry(self) -> None:
        """Return the first srcset entry URL."""
        srcset = "https://ex.co/1.jpg 1x, https://ex.co/2.jpg 2x"
        assert first_srcset_url(srcset) == "https://ex.co/1.jpg"

    def test_single_entry(self) -> None:
        """Handle a single srcset entry."""
        assert first_srcset_url(" https://ex.co/one.jpg ") == "https://ex.co/one.jpg"
