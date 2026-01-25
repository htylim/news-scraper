"""Tests for the scraper module."""

from unittest.mock import MagicMock, patch

import pytest

from news_scraper.browser import BrowserError
from news_scraper.db.models import Source
from news_scraper.parsers import Article, ParserNotFoundError
from news_scraper.scraper import (
    SUMMARY_MAX_LENGTH,
    ScraperError,
    format_article,
    print_articles,
    scrape,
)


class TestScrape:
    """Tests for the scrape function."""

    def test_scrape_returns_articles(self) -> None:
        """Test scrape returns parsed articles."""
        source = Source(name="infobae", url="https://www.infobae.com")
        mock_html = "<html><body><article>Test</article></body></html>"
        expected_articles = [
            Article(headline="Test", url="https://www.infobae.com/test")
        ]

        with (
            patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch,
            patch("news_scraper.scraper.get_parser") as mock_get_parser,
        ):
            mock_fetch.return_value = mock_html
            mock_parser = MagicMock()
            mock_parser.parse.return_value = expected_articles
            mock_get_parser.return_value = mock_parser

            result = scrape(source)

            assert result == expected_articles
            mock_fetch.assert_called_once_with("https://www.infobae.com")
            mock_parser.parse.assert_called_once_with(mock_html)

    def test_scrape_uses_source_url(self) -> None:
        """Test scrape passes source URL to fetch function."""
        source = Source(name="infobae", url="https://www.infobae.com")

        with (
            patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch,
            patch("news_scraper.scraper.get_parser") as mock_get_parser,
        ):
            mock_fetch.return_value = "<html></html>"
            mock_parser = MagicMock()
            mock_parser.parse.return_value = []
            mock_get_parser.return_value = mock_parser

            scrape(source)

            mock_fetch.assert_called_once_with("https://www.infobae.com")

    def test_scrape_raises_for_unknown_source(self) -> None:
        """Test scrape raises ScraperError for unknown source."""
        source = Source(name="unknown", url="https://unknown.com")

        with (
            patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch,
            patch("news_scraper.scraper.get_parser") as mock_get_parser,
        ):
            mock_fetch.return_value = "<html></html>"
            mock_get_parser.side_effect = ParserNotFoundError("unknown")

            with pytest.raises(ScraperError):
                scrape(source)

    def test_scrape_wraps_browser_error(self) -> None:
        """Test scrape wraps BrowserError as ScraperError."""
        source = Source(name="infobae", url="https://www.infobae.com")
        error_message = "Navigation timeout exceeded"

        with patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch:
            mock_fetch.side_effect = BrowserError(error_message, source.url)

            with pytest.raises(ScraperError) as exc_info:
                scrape(source)

            assert exc_info.value.message == error_message
            assert exc_info.value.source_name == source.name


class TestFormatArticle:
    """Tests for format_article function."""

    def test_format_article_basic(self) -> None:
        """Test formatting article with required fields only."""
        article = Article(headline="Test Headline", url="https://example.com")
        result = format_article(article, 1)

        assert "[1] Test Headline" in result
        assert "URL: https://example.com" in result

    def test_format_article_with_summary(self) -> None:
        """Test formatting article with summary."""
        article = Article(
            headline="Test",
            url="https://example.com",
            summary="This is a summary",
        )
        result = format_article(article, 1)

        assert "Summary: This is a summary" in result

    def test_format_article_with_image(self) -> None:
        """Test formatting article with image."""
        article = Article(
            headline="Test",
            url="https://example.com",
            image_url="https://example.com/image.jpg",
        )
        result = format_article(article, 1)

        assert "Image: https://example.com/image.jpg" in result

    def test_format_article_truncates_long_summary(self) -> None:
        """Test that long summaries are truncated at SUMMARY_MAX_LENGTH."""
        long_summary = "x" * (SUMMARY_MAX_LENGTH + 100)
        article = Article(
            headline="Test", url="https://example.com", summary=long_summary
        )
        result = format_article(article, 1)

        assert "..." in result
        # Summary line should contain truncated text
        assert f"{'x' * SUMMARY_MAX_LENGTH}..." in result

    def test_format_article_short_summary_not_truncated(self) -> None:
        """Test that short summaries are not truncated."""
        short_summary = "x" * (SUMMARY_MAX_LENGTH - 10)
        article = Article(
            headline="Test", url="https://example.com", summary=short_summary
        )
        result = format_article(article, 1)

        assert "..." not in result
        assert short_summary in result


class TestPrintArticles:
    """Tests for print_articles function."""

    def test_print_articles_empty(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test printing empty article list."""
        print_articles([])
        captured = capsys.readouterr()

        assert "No articles found" in captured.out

    def test_print_articles_shows_count(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing shows article count."""
        articles = [
            Article(headline="Test 1", url="https://example.com/1"),
            Article(headline="Test 2", url="https://example.com/2"),
        ]
        print_articles(articles)
        captured = capsys.readouterr()

        assert "Found 2 articles" in captured.out
