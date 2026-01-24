"""Tests for the CLI module."""

from typer.testing import CliRunner

from news_scraper import __version__
from news_scraper.cli import app, validate_url

runner = CliRunner()


class TestValidateUrl:
    """Tests for URL validation."""

    def test_valid_http_url(self) -> None:
        """Test that valid HTTP URLs pass validation."""
        assert validate_url("http://example.com")
        assert validate_url("http://example.com/path")
        assert validate_url("http://example.com/path?query=1")

    def test_valid_https_url(self) -> None:
        """Test that valid HTTPS URLs pass validation."""
        assert validate_url("https://example.com")
        assert validate_url("https://www.example.com")
        assert validate_url("https://example.com/path/to/resource")

    def test_valid_url_with_port(self) -> None:
        """Test that URLs with ports pass validation."""
        assert validate_url("http://localhost:8080")
        assert validate_url("https://example.com:443/path")

    def test_valid_ip_url(self) -> None:
        """Test that URLs with IP addresses pass validation."""
        assert validate_url("http://192.168.1.1")
        assert validate_url("http://192.168.1.1:8080/api")

    def test_invalid_url_no_scheme(self) -> None:
        """Test that URLs without scheme fail validation."""
        assert not validate_url("example.com")
        assert not validate_url("www.example.com")

    def test_invalid_url_wrong_scheme(self) -> None:
        """Test that URLs with wrong scheme fail validation."""
        assert not validate_url("ftp://example.com")
        assert not validate_url("file:///path/to/file")

    def test_invalid_url_empty(self) -> None:
        """Test that empty strings fail validation."""
        assert not validate_url("")

    def test_invalid_url_random_string(self) -> None:
        """Test that random strings fail validation."""
        assert not validate_url("not a url")
        assert not validate_url("http://")


class TestCliScrape:
    """Tests for the scrape command."""

    def test_valid_url_prints_url(self) -> None:
        """Test that a valid URL is printed to stdout."""
        result = runner.invoke(app, ["https://example.com"])
        assert result.exit_code == 0
        assert "https://example.com" in result.stdout

    def test_valid_url_with_verbose(self) -> None:
        """Test that verbose flag works with valid URL."""
        result = runner.invoke(app, ["--verbose", "https://example.com"])
        assert result.exit_code == 0
        assert "https://example.com" in result.stdout

    def test_invalid_url_returns_error(self) -> None:
        """Test that invalid URL returns error exit code."""
        result = runner.invoke(app, ["not-a-valid-url"])
        assert result.exit_code == 1
        assert "Invalid URL" in result.stdout or "Error" in result.stdout

    def test_invalid_url_no_scheme(self) -> None:
        """Test that URL without scheme returns error."""
        result = runner.invoke(app, ["example.com"])
        assert result.exit_code == 1


class TestCliVersion:
    """Tests for version flag."""

    def test_version_flag(self) -> None:
        """Test that --version flag shows version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_version_with_url(self) -> None:
        """Test that --version takes precedence over URL argument."""
        result = runner.invoke(app, ["--version", "https://example.com"])
        assert result.exit_code == 0
        assert __version__ in result.stdout


class TestCliHelp:
    """Tests for help flag."""

    def test_help_flag(self) -> None:
        """Test that --help flag shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "URL to scrape" in result.stdout

    def test_help_shows_options(self) -> None:
        """Test that help shows all options."""
        result = runner.invoke(app, ["--help"])
        assert "--verbose" in result.stdout
        assert "--version" in result.stdout
        assert "--help" in result.stdout
