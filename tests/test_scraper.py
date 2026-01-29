"""Tests for the scraper module."""

from unittest.mock import MagicMock, patch

import pytest

from news_scraper.browser import BrowserError
from news_scraper.db.models import Source
from news_scraper.parsers import ParsedArticle, ParserNotFoundError
from news_scraper.scraper import (
    SUMMARY_MAX_LENGTH,
    ScraperError,
    ScrapeResult,
    format_article,
    print_scrape_result,
    scrape,
)


class TestScrape:
    """Tests for the scrape function."""

    def test_scrape_returns_scrape_result(self) -> None:
        """Test scrape returns ScrapeResult with stats."""
        source = Source(name="infobae", url="https://www.infobae.com")
        source.id = 1
        mock_html = "<html></html>"
        expected_articles = [
            ParsedArticle(
                headline="Test", url="https://www.infobae.com/test", position=1
            )
        ]

        with (
            patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch,
            patch("news_scraper.scraper.get_parser") as mock_get_parser,
            patch("news_scraper.scraper.get_session") as mock_get_session,
            patch("news_scraper.scraper.ArticleRepository") as mock_repo_class,
        ):
            mock_fetch.return_value = mock_html
            mock_parser = MagicMock()
            mock_parser.parse.return_value = expected_articles
            mock_get_parser.return_value = mock_parser

            # Mock session and repository
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_repo = MagicMock()
            mock_repo.bulk_upsert_from_parsed.return_value = (1, 0, 0)
            mock_repo_class.return_value = mock_repo

            result = scrape(source)

            assert isinstance(result, ScrapeResult)
            assert result.articles == expected_articles
            assert result.created_count == 1
            assert result.updated_count == 0
            assert result.skipped_count == 0

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

    def test_scrape_empty_parse_result(self) -> None:
        """Test scrape handles parser returning empty list."""
        source = Source(name="infobae", url="https://www.infobae.com")
        source.id = 1

        with (
            patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch,
            patch("news_scraper.scraper.get_parser") as mock_get_parser,
            patch("news_scraper.scraper.get_session") as mock_get_session,
            patch("news_scraper.scraper.ArticleRepository") as mock_repo_class,
        ):
            mock_fetch.return_value = "<html></html>"
            mock_parser = MagicMock()
            mock_parser.parse.return_value = []
            mock_get_parser.return_value = mock_parser

            # Mock session and repository
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_repo = MagicMock()
            mock_repo.bulk_upsert_from_parsed.return_value = (0, 0, 0)
            mock_repo_class.return_value = mock_repo

            result = scrape(source)

            assert result.articles == []
            assert result.created_count == 0
            assert result.updated_count == 0
            assert result.skipped_count == 0


class TestFormatArticle:
    """Tests for format_article function."""

    def test_format_article_basic(self) -> None:
        """Test formatting article with required fields only."""
        article = ParsedArticle(
            headline="Test Headline", url="https://example.com", position=1
        )
        result = format_article(article, 1)

        assert "[1] Test Headline" in result
        assert "URL: https://example.com" in result

    def test_format_article_includes_position(self) -> None:
        """Test formatting includes position."""
        article = ParsedArticle(
            headline="Test Headline", url="https://example.com", position=5
        )
        result = format_article(article, 1)

        assert "Position: 5" in result

    def test_format_article_with_summary(self) -> None:
        """Test formatting article with summary."""
        article = ParsedArticle(
            headline="Test",
            url="https://example.com",
            position=1,
            summary="This is a summary",
        )
        result = format_article(article, 1)

        assert "Summary: This is a summary" in result

    def test_format_article_with_image(self) -> None:
        """Test formatting article with image."""
        article = ParsedArticle(
            headline="Test",
            url="https://example.com",
            position=1,
            image_url="https://example.com/image.jpg",
        )
        result = format_article(article, 1)

        assert "Image: https://example.com/image.jpg" in result

    def test_format_article_truncates_long_summary(self) -> None:
        """Test that long summaries are truncated at SUMMARY_MAX_LENGTH."""
        long_summary = "x" * (SUMMARY_MAX_LENGTH + 100)
        article = ParsedArticle(
            headline="Test", url="https://example.com", position=1, summary=long_summary
        )
        result = format_article(article, 1)

        assert "..." in result
        # Summary line should contain truncated text
        assert f"{'x' * SUMMARY_MAX_LENGTH}..." in result

    def test_format_article_short_summary_not_truncated(self) -> None:
        """Test that short summaries are not truncated."""
        short_summary = "x" * (SUMMARY_MAX_LENGTH - 10)
        article = ParsedArticle(
            headline="Test",
            url="https://example.com",
            position=1,
            summary=short_summary,
        )
        result = format_article(article, 1)

        assert "..." not in result
        assert short_summary in result

    def test_format_article_escapes_rich_markup(self) -> None:
        """Test that Rich markup in content is escaped to prevent formatting issues."""
        article = ParsedArticle(
            headline="[red]Breaking[/red] News",
            url="https://example.com/[bold]article",
            position=1,
            summary="This has [blue]colors[/blue]",
            image_url="https://example.com/[img].jpg",
        )
        result = format_article(article, 1)

        # Rich escape converts [ to \[, so escaped brackets should appear
        assert r"\[red]Breaking\[/" in result
        assert r"https://example.com/\[bold]article" in result
        assert r"\[blue]colors\[/" in result
        assert "[red]Breaking[/red]" not in result


class TestPrintScrapeResult:
    """Tests for print_scrape_result function."""

    def test_print_result_empty(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test printing empty result."""
        result = ScrapeResult(
            articles=[],
            created_count=0,
            updated_count=0,
            skipped_count=0,
        )
        print_scrape_result(result)
        captured = capsys.readouterr()

        assert "No articles found" in captured.out

    def test_print_result_shows_counts(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing shows article counts."""
        result = ScrapeResult(
            articles=[
                ParsedArticle(headline="Test", url="https://example.com/1", position=1),
            ],
            created_count=5,
            updated_count=3,
            skipped_count=0,
        )
        print_scrape_result(result)
        captured = capsys.readouterr()

        assert "New: 5" in captured.out
        assert "Updated: 3" in captured.out

    def test_print_result_shows_skipped_when_nonzero(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing shows skipped count when > 0."""
        result = ScrapeResult(
            articles=[
                ParsedArticle(headline="Test", url="https://example.com/1", position=1),
            ],
            created_count=5,
            updated_count=3,
            skipped_count=2,
        )
        print_scrape_result(result)
        captured = capsys.readouterr()

        assert "Skipped" in captured.out
        assert "2" in captured.out

    def test_print_result_shows_article_count(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing shows total article count."""
        result = ScrapeResult(
            articles=[
                ParsedArticle(
                    headline="Test 1", url="https://example.com/1", position=1
                ),
                ParsedArticle(
                    headline="Test 2", url="https://example.com/2", position=2
                ),
            ],
            created_count=2,
            updated_count=0,
            skipped_count=0,
        )
        print_scrape_result(result)
        captured = capsys.readouterr()

        assert "Found 2 articles" in captured.out
