"""CLI module for news-scraper."""

import re
from typing import Annotated

import structlog
import typer
from rich.console import Console

from news_scraper import __version__

# Configure structlog with simple console output
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
    cache_logger_on_first_use=False,
)

log: structlog.stdlib.BoundLogger = structlog.get_logger()
console = Console()

# URL validation pattern
URL_PATTERN = re.compile(
    r"^https?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
    r"localhost|"  # localhost
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IP
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


class InvalidURLError(Exception):
    """Exception raised when an invalid URL is provided."""

    def __init__(self, url: str, message: str = "Invalid URL format") -> None:
        """Initialize InvalidURLError.

        Args:
            url: The invalid URL that was provided.
            message: Error message describing the issue.
        """
        self.url = url
        self.message = message
        super().__init__(f"{message}: {url}")


def validate_url(url: str) -> bool:
    """Validate if a string is a valid URL.

    Args:
        url: The URL string to validate.

    Returns:
        True if the URL is valid, False otherwise.
    """
    return bool(URL_PATTERN.match(url))


def version_callback(value: bool) -> None:
    """Print version and exit.

    Args:
        value: Whether the version flag was provided.
    """
    if value:
        console.print(f"news-scraper version {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="news-scraper",
    help="A professional CLI for scraping news articles from URLs.",
    add_completion=False,
)


@app.command()
def scrape(
    url: Annotated[str, typer.Argument(help="URL to scrape")],
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
    """Scrape a news article from the given URL."""
    if verbose:
        log.debug("Verbose mode enabled")

    # Validate URL
    if not validate_url(url):
        log.error("Invalid URL provided", url=url)
        console.print(f"[red]Error:[/red] Invalid URL format: {url}")
        raise typer.Exit(code=1)

    # Log and print the URL
    log.info("Processing URL", url=url)
    console.print(f"[green]URL:[/green] {url}")


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
