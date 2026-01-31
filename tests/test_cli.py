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
from news_scraper.parsers import ParsedArticle
from news_scraper.scraper import ScraperError, ScrapeResult

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
    def mock_scrape_fn(source: Source) -> ScrapeResult:
        return ScrapeResult(
            articles=[
                ParsedArticle(
                    headline="Test Article",
                    url=f"https://{source.name}.com/article",
                    position=1,
                )
            ],
            created_count=1,
            updated_count=0,
            skipped_count=0,
        )

    monkeypatch.setattr("news_scraper.cli.scrape", mock_scrape_fn)

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

        result = runner.invoke(app, ["scrape", "infobae"])
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
        result = runner.invoke(app, ["scrape", "clarin"])
        assert result.exit_code == 0
        assert "Scraping clarin" in result.stdout
        # Ensure other sources are NOT in output
        assert "infobae" not in result.stdout or "Scraping infobae" not in result.stdout
        assert (
            "lanacion" not in result.stdout or "Scraping lanacion" not in result.stdout
        )

    def test_scrape_case_insensitive_lookup(self, cli_db_session: Session) -> None:
        """Test source lookup is case-insensitive."""
        source = Source(name="infobae", url="https://infobae.com")
        cli_db_session.add(source)
        cli_db_session.commit()

        # Uppercase input should find lowercase source
        result = runner.invoke(app, ["scrape", "INFOBAE"])
        assert result.exit_code == 0
        assert "Scraping infobae" in result.stdout

    def test_scrape_mixed_case_lookup(self, cli_db_session: Session) -> None:
        """Test mixed case input is normalized."""
        source = Source(name="lanacion", url="https://lanacion.com.ar")
        cli_db_session.add(source)
        cli_db_session.commit()

        result = runner.invoke(app, ["scrape", "LaNacion"])
        assert result.exit_code == 0
        assert "Scraping lanacion" in result.stdout

    def test_scrape_with_verbose(self, cli_db_session: Session) -> None:
        """Test verbose flag works with scrape command."""
        source = Source(name="verbosesrc", url="https://verbose.com")
        cli_db_session.add(source)
        cli_db_session.commit()

        result = runner.invoke(app, ["-v", "scrape", "verbosesrc"])
        assert result.exit_code == 0
        assert "Scraping verbosesrc" in result.stdout

    def test_scrape_all_enabled_sources(self, cli_db_session: Session) -> None:
        """Test scraping all enabled sources when no source names provided."""
        sources = [
            Source(name="infobae", url="https://infobae.com"),
            Source(name="clarin", url="https://clarin.com"),
            Source(name="lanacion", url="https://lanacion.com.ar"),
        ]
        for s in sources:
            cli_db_session.add(s)
        cli_db_session.commit()

        result = runner.invoke(app, ["scrape"])
        assert result.exit_code == 0
        assert "Scraping clarin" in result.stdout
        assert "Scraping infobae" in result.stdout
        assert "Scraping lanacion" in result.stdout

    def test_scrape_all_skips_disabled_sources(self, cli_db_session: Session) -> None:
        """Test that scraping all sources skips disabled ones."""
        sources = [
            Source(name="enabled1", url="https://enabled1.com"),
            Source(name="disabled", url="https://disabled.com", is_enabled=False),
            Source(name="enabled2", url="https://enabled2.com"),
        ]
        for s in sources:
            cli_db_session.add(s)
        cli_db_session.commit()

        result = runner.invoke(app, ["scrape"])
        assert result.exit_code == 0
        assert "Scraping enabled1" in result.stdout
        assert "Scraping enabled2" in result.stdout
        assert "Scraping disabled" not in result.stdout

    def test_scrape_all_no_enabled_sources(self, cli_db_session: Session) -> None:
        """Test error when no enabled sources exist."""
        source = Source(name="disabled", url="https://disabled.com", is_enabled=False)
        cli_db_session.add(source)
        cli_db_session.commit()

        result = runner.invoke(app, ["scrape"])
        assert result.exit_code == 1
        assert "No enabled sources found" in result.stdout

    def test_scrape_multiple_sources(self, cli_db_session: Session) -> None:
        """Test scraping multiple sources in one command."""
        sources = [
            Source(name="infobae", url="https://infobae.com"),
            Source(name="clarin", url="https://clarin.com"),
            Source(name="lanacion", url="https://lanacion.com.ar"),
        ]
        for s in sources:
            cli_db_session.add(s)
        cli_db_session.commit()

        result = runner.invoke(app, ["scrape", "clarin", "infobae"])
        assert result.exit_code == 0
        # Should scrape in order provided
        output = result.stdout
        clarin_pos = output.find("Scraping clarin")
        infobae_pos = output.find("Scraping infobae")
        assert clarin_pos != -1
        assert infobae_pos != -1
        assert clarin_pos < infobae_pos
        assert "Scraping lanacion" not in result.stdout

    def test_scrape_multiple_sources_deduplicates(
        self, cli_db_session: Session
    ) -> None:
        """Test that duplicate source names are deduplicated."""
        source = Source(name="infobae", url="https://infobae.com")
        cli_db_session.add(source)
        cli_db_session.commit()

        result = runner.invoke(app, ["scrape", "infobae", "INFOBAE", "infobae"])
        assert result.exit_code == 0
        # Should only scrape once
        assert result.stdout.count("Scraping infobae") == 1

    def test_scrape_multiple_sources_case_insensitive_dedup(
        self, cli_db_session: Session
    ) -> None:
        """Test that case variations are deduplicated."""
        source = Source(name="infobae", url="https://infobae.com")
        cli_db_session.add(source)
        cli_db_session.commit()

        result = runner.invoke(app, ["scrape", "infobae", "INFOBAE"])
        assert result.exit_code == 0
        assert result.stdout.count("Scraping infobae") == 1

    def test_source_not_found(self, cli_db_session: Session) -> None:
        """Test error when source doesn't exist."""
        _ = cli_db_session  # Ensure fixture is active for get_session patch
        result = runner.invoke(app, ["scrape", "nonexistent"])
        assert result.exit_code == 1
        assert "Source not found or disabled" in result.stdout
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

        result = runner.invoke(app, ["scrape", "nonexistent"])
        assert result.exit_code == 1
        assert "Source not found or disabled" in result.stdout

    def test_source_disabled(self, cli_db_session: Session) -> None:
        """Test error when source is disabled."""
        source = Source(name="disabled", url="https://disabled.com", is_enabled=False)
        cli_db_session.add(source)
        cli_db_session.commit()

        result = runner.invoke(app, ["scrape", "disabled"])
        assert result.exit_code == 1
        assert "Source not found or disabled" in result.stdout
        assert "disabled" in result.stdout

    def test_multiple_sources_one_missing(self, cli_db_session: Session) -> None:
        """Test that if any source is missing, command fails without scraping."""
        source = Source(name="infobae", url="https://infobae.com")
        cli_db_session.add(source)
        cli_db_session.commit()

        result = runner.invoke(app, ["scrape", "infobae", "nonexistent"])
        assert result.exit_code == 1
        assert "Source not found or disabled" in result.stdout
        assert "nonexistent" in result.stdout
        # Should not scrape infobae since validation failed
        assert "Scraping infobae" not in result.stdout

    def test_multiple_sources_one_disabled(self, cli_db_session: Session) -> None:
        """Test that if any source is disabled, command fails without scraping."""
        sources = [
            Source(name="enabled", url="https://enabled.com"),
            Source(name="disabled", url="https://disabled.com", is_enabled=False),
        ]
        for s in sources:
            cli_db_session.add(s)
        cli_db_session.commit()

        result = runner.invoke(app, ["scrape", "enabled", "disabled"])
        assert result.exit_code == 1
        assert "Source not found or disabled" in result.stdout
        assert "disabled" in result.stdout
        # Should not scrape enabled since validation failed
        assert "Scraping enabled" not in result.stdout

    def test_invalid_source_name_with_spaces(self) -> None:
        """Test error when source name contains spaces."""
        result = runner.invoke(app, ["scrape", "invalid source"])
        assert result.exit_code == 1
        assert (
            "must contain only" in result.stdout.lower()
            or "invalid" in result.stdout.lower()
        )

    def test_invalid_source_name_with_special_chars(self) -> None:
        """Test error when source name contains invalid characters."""
        result = runner.invoke(app, ["scrape", "source@name!"])
        assert result.exit_code == 1

    def test_invalid_source_name_empty(self) -> None:
        """Test error when source name is empty."""
        result = runner.invoke(app, ["scrape", ""])
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

        result = runner.invoke(app, ["scrape", "failsource"])
        assert result.exit_code == 1
        assert "Failed to scrape failsource" in result.stdout
        assert "Connection timed out" in result.stdout

    def test_scraper_error_continues_with_multiple_sources(
        self, cli_db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that ScraperError in one source doesn't stop other sources."""
        sources = [
            Source(name="success", url="https://success.com"),
            Source(name="failure", url="https://failure.com"),
        ]
        for s in sources:
            cli_db_session.add(s)
        cli_db_session.commit()

        # Mock scrape to fail for "failure" source
        def mock_scrape_fn(source: Source) -> ScrapeResult:
            if source.name == "failure":
                raise ScraperError(
                    message="Connection timed out", source_name="failure"
                )
            print(f"Scraping {source.name}")
            return ScrapeResult(
                articles=[
                    ParsedArticle(
                        headline="Test Article",
                        url=f"https://{source.name}.com/article",
                        position=1,
                    )
                ],
                created_count=1,
                updated_count=0,
                skipped_count=0,
            )

        monkeypatch.setattr("news_scraper.cli.scrape", mock_scrape_fn)

        result = runner.invoke(app, ["scrape", "success", "failure"])
        assert result.exit_code == 1  # Should exit with error code
        assert "Scraping success" in result.stdout
        assert "Failed to scrape failure" in result.stdout
        assert "Connection timed out" in result.stdout


class TestCliVersion:
    """Tests for version flag."""

    def test_version_flag(self) -> None:
        """Test that --version flag shows version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_version_short_flag(self) -> None:
        """Test that version works on root command."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout


class TestCliHelp:
    """Tests for help flag."""

    def test_help_flag(self) -> None:
        """Test that --help flag shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "scrape" in result.stdout

    def test_help_shows_options(self) -> None:
        """Test that help shows all options."""
        result = runner.invoke(app, ["--help"])
        assert "--verbose" in result.stdout
        assert "--version" in result.stdout
        assert "--help" in result.stdout
        assert "--source" not in result.stdout

    def test_scrape_help(self) -> None:
        """Test that scrape command has help."""
        result = runner.invoke(app, ["scrape", "--help"])
        assert result.exit_code == 0
        assert "Source name(s) to scrape" in result.stdout
