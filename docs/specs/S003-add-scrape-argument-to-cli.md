# S003: Add Source Argument to CLI

Add `-s <source>` argument to scrape a news source by name.

## Goal

Enable running the scraper for a specific source from the database:

```bash
news-scraper -s infobae
```

This replaces the placeholder URL-based command with a database-driven approach.

## Deliverables

### 1. Validation Module

**File:** `src/news_scraper/validation.py`

Reusable validation utilities. The slug pattern allows:
- Lowercase letters (a-z)
- Numbers (0-9)
- Hyphens (-) and underscores (_)
- Must start with a letter or number
- Min length: 1, Max length: 100

```python
"""Validation utilities for news-scraper."""

import re

# Slug pattern: lowercase alphanumeric, hyphens, underscores
# Must start with letter or number, no consecutive special chars
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SLUG_MAX_LENGTH = 100


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def validate_slug(value: str, field_name: str = "value") -> str:
    """Validate and normalize a slug string.

    Args:
        value: The string to validate.
        field_name: Name of the field for error messages.

    Returns:
        The normalized (lowercase) slug.

    Raises:
        ValidationError: If the value is not a valid slug.
    """
    if not value:
        raise ValidationError(field_name, "cannot be empty")

    # Normalize to lowercase
    normalized = value.lower()

    if len(normalized) > SLUG_MAX_LENGTH:
        raise ValidationError(
            field_name, f"cannot exceed {SLUG_MAX_LENGTH} characters"
        )

    if not SLUG_PATTERN.match(normalized):
        raise ValidationError(
            field_name,
            "must contain only lowercase letters, numbers, hyphens, and underscores, "
            "and must start with a letter or number",
        )

    return normalized


def is_valid_slug(value: str) -> bool:
    """Check if a string is a valid slug without raising.

    Args:
        value: The string to check.

    Returns:
        True if valid, False otherwise.
    """
    try:
        validate_slug(value)
        return True
    except ValidationError:
        return False
```

### 2. Updated Source Model

**File:** `src/news_scraper/db/models/source.py`

Add app-level validation using SQLAlchemy's `@validates` decorator.

```python
"""Source model for news sources."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, validates

from news_scraper.db.base import Base, TimestampMixin
from news_scraper.validation import ValidationError, validate_slug


class Source(TimestampMixin, Base):
    """News source configuration."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        """Validate and normalize name as a slug.

        Args:
            key: The attribute name (always "name").
            value: The value being set.

        Returns:
            The normalized lowercase slug.

        Raises:
            ValueError: If the name is not a valid slug.
        """
        try:
            return validate_slug(value, field_name="name")
        except ValidationError as e:
            raise ValueError(str(e)) from e

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, name={self.name!r})>"
```

Notes:
- `@validates` runs on attribute assignment, before flush
- Raises `ValueError` (standard Python) not `ValidationError` for SQLAlchemy compatibility
- Name is normalized to lowercase automatically

### 3. Logging Configuration Module

**File:** `src/news_scraper/logging.py`

Move structlog configuration out of `cli.py` into a dedicated module. This ensures:
- Configuration runs once, not on every import
- Testable in isolation
- Consistent logging across all entry points

```python
"""Logging configuration for news-scraper."""

import structlog


def configure_logging() -> None:
    """Configure structlog for the application.

    Call once at application startup.
    """
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger() -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger()
```

Note: `cache_logger_on_first_use=True` for production (was `False` before).

### 2. Scraper Module

**File:** `src/news_scraper/scraper.py`

New module containing the scrape logic (placeholder for now).

```python
"""Scraper module for news sources."""

from news_scraper.db.models import Source


def scrape(source: Source) -> None:
    """Scrape news from the given source.

    Args:
        source: The source to scrape.
    """
    print(f"Scraping {source.name}")
```

### 5. Refactored CLI

**File:** `src/news_scraper/cli.py`

Replace the URL-based `scrape` command with source-based approach.

#### Changes

1. Remove URL validation code (no longer needed)
2. Remove `InvalidURLError` exception (no longer needed)
3. Remove `validate_url` function (no longer needed)
4. Remove `URL_PATTERN` constant (no longer needed)
5. Move structlog configuration to `logging.py`
6. Add `-s/--source` option
7. Validate and normalize source name (case-insensitive, slug format)
8. Lookup source by normalized name in database using SQLAlchemy 2.0 style
9. Handle validation errors and source not found error
10. Call `scrape()` function

#### New Implementation

```python
"""CLI module for news-scraper."""

from typing import Annotated

import typer
from rich.console import Console
from sqlalchemy import select

from news_scraper import __version__
from news_scraper.db import get_session
from news_scraper.db.models import Source
from news_scraper.logging import configure_logging, get_logger
from news_scraper.scraper import scrape
from news_scraper.validation import ValidationError, validate_slug

console = Console()

app = typer.Typer(
    name="news-scraper",
    help="A professional CLI for scraping news articles.",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit.

    Args:
        value: Whether the version flag was provided.
    """
    if value:
        console.print(f"news-scraper version {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    source_name: Annotated[
        str | None, typer.Option("--source", "-s", help="Source name to scrape")
    ] = None,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose output")
    ] = False,
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
) -> None:
    """Scrape news from a configured source."""
    # Initialize logging once at startup
    configure_logging()
    log = get_logger()

    if verbose:
        log.debug("Verbose mode enabled")

    # Source is required when not showing help/version
    if source_name is None:
        console.print("[red]Error:[/red] Missing required option: --source / -s")
        raise typer.Exit(code=1)

    # Validate and normalize source name (case-insensitive)
    try:
        normalized_name = validate_slug(source_name, field_name="source")
    except ValidationError as e:
        log.error("Invalid source name", source=source_name, error=str(e))
        console.print(f"[red]Error:[/red] {e.message}")
        raise typer.Exit(code=1)

    # Lookup source by normalized name (SQLAlchemy 2.0 style)
    with get_session() as session:
        stmt = select(Source).where(Source.name == normalized_name)
        source = session.scalars(stmt).first()

        if source is None:
            log.error("Source not found", source=normalized_name)
            console.print(f"[red]Error:[/red] Source not found: {normalized_name}")
            raise typer.Exit(code=1)

        if not source.is_enabled:
            log.error("Source is disabled", source=normalized_name)
            console.print(f"[red]Error:[/red] Source is disabled: {normalized_name}")
            raise typer.Exit(code=1)

        log.info("Scraping source", source=normalized_name)
        scrape(source)


if __name__ == "__main__":
    app()
```

#### Key Design Decisions

1. **Required `-s` option**: Source is required. CLI exits with error if not provided.
2. **Case-insensitive lookup**: Input is normalized to lowercase via `validate_slug()`.
3. **Slug validation**: Source names must be valid slugs (alphanumeric, hyphens, underscores).
4. **Disabled source check**: If a source exists but `is_enabled=False`, show error.
5. **Session scope**: Database session is active during scrape so Source object remains valid.
6. **SQLAlchemy 2.0 style**: Uses `select()` and `session.scalars()` instead of legacy `session.query()`.
7. **Logging init at startup**: `configure_logging()` called in command, not at module import.

### 6. Entry Point

**File:** `pyproject.toml`

No change needed. Entry point remains:

```toml
[project.scripts]
news-scraper = "news_scraper.cli:app"
```

Typer's `app` handles invocation directly.

### 7. Updated Tests

**File:** `tests/test_cli.py`

Replace URL-based tests with source-based tests.

```python
"""Tests for the CLI module."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from typer.testing import CliRunner

from news_scraper import __version__
from news_scraper.cli import app
from news_scraper.db.base import Base
from news_scraper.db.models import Source


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
        source = Source(
            name="disabled", url="https://disabled.com", is_enabled=False
        )
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
        assert "must contain only" in result.stdout.lower() or "invalid" in result.stdout.lower()

    def test_invalid_source_name_with_special_chars(self) -> None:
        """Test error when source name contains invalid characters."""
        result = runner.invoke(app, ["-s", "source@name!"])
        assert result.exit_code == 1

    def test_invalid_source_name_empty(self) -> None:
        """Test error when source name is empty."""
        result = runner.invoke(app, ["-s", ""])
        assert result.exit_code == 1


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
```

### 8. Scraper Tests

**File:** `tests/test_scraper.py`

```python
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

    def test_scrape_different_sources(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test scrape prints correct name for different sources."""
        source1 = Source(name="infobae", url="https://infobae.com")
        source2 = Source(name="clarin", url="https://clarin.com")

        scrape(source1)
        captured1 = capsys.readouterr()
        assert "Scraping infobae" in captured1.out

        scrape(source2)
        captured2 = capsys.readouterr()
        assert "Scraping clarin" in captured2.out
```

Note: The `Source` object is created directly without database for unit testing the scrape function in isolation.

### 9. Validation Tests

**File:** `tests/test_validation.py`

```python
"""Tests for the validation module."""

import pytest

from news_scraper.validation import (
    ValidationError,
    is_valid_slug,
    validate_slug,
)


class TestValidateSlug:
    """Tests for validate_slug function."""

    def test_valid_lowercase_slug(self) -> None:
        """Test valid lowercase slug passes."""
        assert validate_slug("infobae") == "infobae"

    def test_valid_slug_with_numbers(self) -> None:
        """Test slug with numbers passes."""
        assert validate_slug("news24") == "news24"

    def test_valid_slug_with_hyphen(self) -> None:
        """Test slug with hyphen passes."""
        assert validate_slug("la-nacion") == "la-nacion"

    def test_valid_slug_with_underscore(self) -> None:
        """Test slug with underscore passes."""
        assert validate_slug("la_nacion") == "la_nacion"

    def test_normalizes_to_lowercase(self) -> None:
        """Test uppercase is normalized to lowercase."""
        assert validate_slug("INFOBAE") == "infobae"
        assert validate_slug("LaNacion") == "lanacion"

    def test_empty_string_raises(self) -> None:
        """Test empty string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("")
        assert "cannot be empty" in str(exc_info.value)

    def test_whitespace_raises(self) -> None:
        """Test string with whitespace raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("invalid source")

    def test_special_characters_raise(self) -> None:
        """Test special characters raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("source@name")
        with pytest.raises(ValidationError):
            validate_slug("source!name")
        with pytest.raises(ValidationError):
            validate_slug("source.name")

    def test_starting_with_hyphen_raises(self) -> None:
        """Test slug starting with hyphen raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("-invalid")

    def test_starting_with_underscore_raises(self) -> None:
        """Test slug starting with underscore raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("_invalid")

    def test_too_long_raises(self) -> None:
        """Test slug exceeding max length raises ValidationError."""
        long_slug = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            validate_slug(long_slug)
        assert "cannot exceed" in str(exc_info.value)

    def test_max_length_passes(self) -> None:
        """Test slug at max length passes."""
        max_slug = "a" * 100
        assert validate_slug(max_slug) == max_slug

    def test_custom_field_name_in_error(self) -> None:
        """Test custom field name appears in error message."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("", field_name="source")
        assert "source" in str(exc_info.value)


class TestIsValidSlug:
    """Tests for is_valid_slug function."""

    def test_valid_slug_returns_true(self) -> None:
        """Test valid slug returns True."""
        assert is_valid_slug("infobae") is True
        assert is_valid_slug("la-nacion") is True
        assert is_valid_slug("news_24") is True

    def test_invalid_slug_returns_false(self) -> None:
        """Test invalid slug returns False."""
        assert is_valid_slug("") is False
        assert is_valid_slug("invalid source") is False
        assert is_valid_slug("-invalid") is False
```

### 10. Logging Tests

**File:** `tests/test_logging.py`

```python
"""Tests for the logging module."""

from news_scraper.logging import configure_logging, get_logger


class TestLogging:
    """Tests for logging configuration."""

    def test_configure_logging_runs_without_error(self) -> None:
        """Test configure_logging can be called."""
        configure_logging()  # Should not raise

    def test_get_logger_returns_bound_logger(self) -> None:
        """Test get_logger returns a structlog logger."""
        configure_logging()
        log = get_logger()
        assert log is not None
        # Verify it's a structlog logger by checking it has expected methods
        assert hasattr(log, "info")
        assert hasattr(log, "error")
        assert hasattr(log, "debug")
```

### 11. Updated Model Tests

**File:** `tests/db/test_models.py`

Add validation tests to existing Source model tests.

```python
# Add to existing TestSourceModel class:

def test_name_normalized_to_lowercase(self, db_session: Session) -> None:
    """Test name is normalized to lowercase on creation."""
    source = Source(name="INFOBAE", url="https://infobae.com")
    db_session.add(source)
    db_session.commit()

    assert source.name == "infobae"

def test_name_with_valid_slug_chars(self, db_session: Session) -> None:
    """Test name with valid slug characters."""
    source = Source(name="la-nacion_24", url="https://lanacion.com")
    db_session.add(source)
    db_session.commit()

    assert source.name == "la-nacion_24"

def test_name_with_spaces_raises(self, db_session: Session) -> None:
    """Test name with spaces raises ValueError."""
    with pytest.raises(ValueError):
        Source(name="invalid source", url="https://invalid.com")

def test_name_with_special_chars_raises(self, db_session: Session) -> None:
    """Test name with special characters raises ValueError."""
    with pytest.raises(ValueError):
        Source(name="source@name", url="https://invalid.com")

def test_empty_name_raises(self, db_session: Session) -> None:
    """Test empty name raises ValueError."""
    with pytest.raises(ValueError):
        Source(name="", url="https://invalid.com")
```

## File Summary

**New files:**
- `src/news_scraper/validation.py` - Slug validation utilities
- `src/news_scraper/logging.py` - Centralized structlog configuration
- `src/news_scraper/scraper.py` - Scraper module with placeholder
- `tests/test_validation.py` - Validation unit tests
- `tests/test_scraper.py` - Scraper unit tests
- `tests/test_logging.py` - Logging configuration tests

**Modified files:**
- `src/news_scraper/cli.py` - Refactored to use `-s` option, removed URL handling
- `src/news_scraper/db/models/source.py` - Added `@validates` for name field
- `tests/test_cli.py` - Replace URL tests with source tests
- `tests/db/test_models.py` - Add validation tests for Source model

**Removed code from cli.py:**
- `InvalidURLError` class
- `validate_url` function
- `URL_PATTERN` constant
- `url` argument from scrape command
- Inline structlog configuration (moved to `logging.py`)

## Acceptance Criteria

### CLI Functionality
- [ ] `news-scraper -s infobae` looks up "infobae" in Sources table
- [ ] `news-scraper --source infobae` works (long option)
- [ ] `news-scraper -s INFOBAE` finds "infobae" (case-insensitive)
- [ ] Source found: prints "Scraping infobae" and exits 0
- [ ] Source not found: prints error and exits 1
- [ ] Source disabled: prints error and exits 1
- [ ] Correct source selected when multiple sources exist in DB
- [ ] `-s` option is required (no default)
- [ ] `--version` flag still works
- [ ] `--verbose` flag still works
- [ ] `-v` short flag for verbose works
- [ ] `--help` shows new options

### Validation
- [ ] Source names normalized to lowercase
- [ ] Valid slugs: alphanumeric, hyphens, underscores
- [ ] Invalid: spaces, special characters, starting with hyphen/underscore
- [ ] Max length: 100 characters
- [ ] CLI shows error for invalid source name format
- [ ] Source model rejects invalid names on assignment

### Infrastructure
- [ ] Logging configured via `logging.py`, not at import time
- [ ] `ValidationError` exception for validation failures
- [ ] `validate_slug()` and `is_valid_slug()` utilities available

### Quality
- [ ] All tests pass
- [ ] mypy passes with strict mode
- [ ] ruff passes
- [ ] pre-commit passes
