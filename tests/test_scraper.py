"""Tests for the scraper module."""

import pytest

from news_scraper.db.models import Source
from news_scraper.scraper import scrape


class TestScrape:
    """Tests for the scrape function."""

    def test_scrape_prints_source_name(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test scrape prints source name."""
        # Create a source object (no DB needed for this test)
        source = Source(name="testsource", url="https://test.com")

        scrape(source)

        captured = capsys.readouterr()
        assert "Scraping testsource" in captured.out

    def test_scrape_different_sources(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test scrape prints correct name for different sources."""
        source1 = Source(name="infobae", url="https://infobae.com")
        source2 = Source(name="clarin", url="https://clarin.com")

        scrape(source1)
        captured1 = capsys.readouterr()
        assert "Scraping infobae" in captured1.out

        scrape(source2)
        captured2 = capsys.readouterr()
        assert "Scraping clarin" in captured2.out
