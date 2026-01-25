"""Tests for the scraper module."""

from unittest.mock import patch

import pytest

from news_scraper.browser import BrowserError
from news_scraper.db.models import Source
from news_scraper.scraper import ScraperError, scrape


class TestScrape:
    """Tests for the scrape function."""

    def test_scrape_prints_html(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test scrape prints rendered HTML to stdout."""
        source = Source(name="testsource", url="https://test.com")
        mock_html = "<html><body>Test content</body></html>"

        with patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch:
            mock_fetch.return_value = mock_html

            scrape(source)

            mock_fetch.assert_called_once_with("https://test.com")
            captured = capsys.readouterr()
            assert mock_html in captured.out

    def test_scrape_uses_source_url(self) -> None:
        """Test scrape passes source URL to fetch function."""
        source = Source(name="infobae", url="https://www.infobae.com")

        with patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch:
            mock_fetch.return_value = "<html></html>"

            scrape(source)

            mock_fetch.assert_called_once_with("https://www.infobae.com")

    def test_scrape_different_sources(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test scrape works with different sources."""
        with patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch:
            source1 = Source(name="infobae", url="https://infobae.com")
            mock_fetch.return_value = "<html>Source 1</html>"
            scrape(source1)
            captured1 = capsys.readouterr()
            assert "<html>Source 1</html>" in captured1.out

            source2 = Source(name="clarin", url="https://clarin.com")
            mock_fetch.return_value = "<html>Source 2</html>"
            scrape(source2)
            captured2 = capsys.readouterr()
            assert "<html>Source 2</html>" in captured2.out

    def test_scrape_raises_scraper_error_on_browser_error(self) -> None:
        """Test scrape raises ScraperError when browser fetch fails."""
        source = Source(name="testsource", url="https://test.com")

        with patch("news_scraper.scraper.fetch_rendered_html") as mock_fetch:
            mock_fetch.side_effect = BrowserError(
                "Connection failed", "https://test.com"
            )

            with pytest.raises(ScraperError) as exc_info:
                scrape(source)

            assert exc_info.value.source_name == "testsource"
            assert "Connection failed" in exc_info.value.message
