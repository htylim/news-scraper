"""Tests for the CLI module."""

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from typer.testing import CliRunner

from news_scraper import __version__
from news_scraper.cli import app
from news_scraper.db.base import Base
from news_scraper.db.models import Source
from news_scraper.scraper import ScraperError

runner = CliRunner()


@pytest.fixture
def cli_db_session(monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    """In-memory database session that patches get_session for CLI tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()

    # Patch get_session to use test session
    from contextlib import contextmanager

    @contextmanager
    def mock_get_session() -> Generator[Session, None, None]:
        yield session

    monkeypatch.setattr("news_scraper.cli.get_session", mock_get_session)

    # Mock scrape to avoid actual browser calls
    mock_scrape = MagicMock()

    def print_scraping(source: Source) -> None:
        print(f"Scraping {source.name}")

    mock_scrape.side_effect = print_scraping
    monkeypatch.setattr("news_scraper.cli.scrape", mock_scrape)

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


class TestCliScrape:
    """Tests for the scrape command."""

    def test_scrape_existing_source(self, cli_db_session: Session) -> None:
        """Test scraping an existing source prints message."""
        source = Source(name="infobae", url="https://infobae.com")
        cli_db_session.add(source)
        cli_db_session.commit()

        result = runner.invoke(app, ["-s", "infobae"])
        assert result.exit_code == 0
        assert "Scraping infobae" in result.stdout

    def test_scrape_correct_source_among_multiple(
        self, cli_db_session: Session
    ) -> None:
        """Test that correct source is selected when multiple exist."""
        # Add multiple sources
        sources = [
            Source(name="infobae", url="https://infobae.com"),
            Source(name="clarin", url="https://clarin.com"),
            Source(name="lanacion", url="https://lanacion.com.ar"),
        ]
        for s in sources:
            cli_db_session.add(s)
        cli_db_session.commit()

        # Request specific source
        result = runner.invoke(app, ["-s", "clarin"])
        assert result.exit_code == 0
        assert "Scraping clarin" in result.stdout
        # Ensure other sources are NOT in output
        assert "infobae" not in result.stdout
        assert "lanacion" not in result.stdout

    def test_scrape_case_insensitive_lookup(self, cli_db_session: Session) -> None:
        """Test source lookup is case-insensitive."""
        source = Source(name="infobae", url="https://infobae.com")
        cli_db_session.add(source)
        cli_db_session.commit()

        # Uppercase input should find lowercase source
        result = runner.invoke(app, ["-s", "INFOBAE"])
        assert result.exit_code == 0
        assert "Scraping infobae" in result.stdout

    def test_scrape_mixed_case_lookup(self, cli_db_session: Session) -> None:
        """Test mixed case input is normalized."""
        source = Source(name="lanacion", url="https://lanacion.com.ar")
        cli_db_session.add(source)
        cli_db_session.commit()

        result = runner.invoke(app, ["-s", "LaNacion"])
        assert result.exit_code == 0
        assert "Scraping lanacion" in result.stdout

    def test_scrape_with_long_option(self, cli_db_session: Session) -> None:
        """Test --source long option works."""
        source = Source(name="testsource", url="https://test.com")
        cli_db_session.add(source)
        cli_db_session.commit()

        result = runner.invoke(app, ["--source", "testsource"])
        assert result.exit_code == 0
        assert "Scraping testsource" in result.stdout

    def test_scrape_with_verbose(self, cli_db_session: Session) -> None:
        """Test verbose flag works with source."""
        source = Source(name="verbosesrc", url="https://verbose.com")
        cli_db_session.add(source)
        cli_db_session.commit()

        result = runner.invoke(app, ["-s", "verbosesrc", "-v"])
        assert result.exit_code == 0
        assert "Scraping verbosesrc" in result.stdout

    def test_source_not_found(self, cli_db_session: Session) -> None:
        """Test error when source doesn't exist."""
        _ = cli_db_session  # Ensure fixture is active for get_session patch
        result = runner.invoke(app, ["-s", "nonexistent"])
        assert result.exit_code == 1
        assert "Source not found" in result.stdout
        assert "nonexistent" in result.stdout

    def test_source_not_found_among_multiple(self, cli_db_session: Session) -> None:
        """Test source not found when other sources exist."""
        sources = [
            Source(name="infobae", url="https://infobae.com"),
            Source(name="clarin", url="https://clarin.com"),
        ]
        for s in sources:
            cli_db_session.add(s)
        cli_db_session.commit()

        result = runner.invoke(app, ["-s", "nonexistent"])
        assert result.exit_code == 1
        assert "Source not found" in result.stdout

    def test_source_disabled(self, cli_db_session: Session) -> None:
        """Test error when source is disabled."""
        source = Source(name="disabled", url="https://disabled.com", is_enabled=False)
        cli_db_session.add(source)
        cli_db_session.commit()

        result = runner.invoke(app, ["-s", "disabled"])
        assert result.exit_code == 1
        assert "Source is disabled" in result.stdout

    def test_missing_source_option(self) -> None:
        """Test error when -s option is missing."""
        result = runner.invoke(app, [])
        assert result.exit_code != 0
        # Check for our custom error message or Typer's default
        assert "Missing" in result.stdout or "--source" in result.stdout

    def test_invalid_source_name_with_spaces(self) -> None:
        """Test error when source name contains spaces."""
        result = runner.invoke(app, ["-s", "invalid source"])
        assert result.exit_code == 1
        assert (
            "must contain only" in result.stdout.lower()
            or "invalid" in result.stdout.lower()
        )

    def test_invalid_source_name_with_special_chars(self) -> None:
        """Test error when source name contains invalid characters."""
        result = runner.invoke(app, ["-s", "source@name!"])
        assert result.exit_code == 1

    def test_invalid_source_name_empty(self) -> None:
        """Test error when source name is empty."""
        result = runner.invoke(app, ["-s", ""])
        assert result.exit_code == 1

    def test_scraper_error_handling(
        self, cli_db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that ScraperError is caught and displays appropriate message."""
        source = Source(name="failsource", url="https://fail.com")
        cli_db_session.add(source)
        cli_db_session.commit()

        # Override the scrape mock to raise ScraperError
        mock_scrape = MagicMock(
            side_effect=ScraperError(
                message="Connection timed out", source_name="failsource"
            )
        )
        monkeypatch.setattr("news_scraper.cli.scrape", mock_scrape)

        result = runner.invoke(app, ["-s", "failsource"])
        assert result.exit_code == 1
        assert "Failed to scrape failsource" in result.stdout
        assert "Connection timed out" in result.stdout


class TestCliVersion:
    """Tests for version flag."""

    def test_version_flag(self) -> None:
        """Test that --version flag shows version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_version_short_flag(self) -> None:
        """Test that version takes precedence."""
        result = runner.invoke(app, ["--version", "-s", "any"])
        assert result.exit_code == 0
        assert __version__ in result.stdout


class TestCliHelp:
    """Tests for help flag."""

    def test_help_flag(self) -> None:
        """Test that --help flag shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--source" in result.stdout
        assert "-s" in result.stdout

    def test_help_shows_options(self) -> None:
        """Test that help shows all options."""
        result = runner.invoke(app, ["--help"])
        assert "--verbose" in result.stdout
        assert "--version" in result.stdout
        assert "--help" in result.stdout
