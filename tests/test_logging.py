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
