"""Logging configuration for news-scraper."""

from typing import Any

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


def get_logger() -> Any:
    """Get a configured logger instance."""
    return structlog.get_logger()
