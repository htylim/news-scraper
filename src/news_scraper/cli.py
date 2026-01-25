"""CLI module for news-scraper."""

from typing import Annotated

import typer
from rich.console import Console
from sqlalchemy import select

from news_scraper import __version__
from news_scraper.db import get_session
from news_scraper.db.models import Source
from news_scraper.logging import configure_logging, get_logger
from news_scraper.scraper import ScraperError, scrape
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
    _ctx: typer.Context,
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
        raise typer.Exit(code=1) from None

    # Lookup source by normalized name (SQLAlchemy 2.0 style)
    # Note: Source names are stored lowercase in the database, and the input
    # has been normalized to lowercase above, so this exact match query is
    # effectively case-insensitive.
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
        try:
            scrape(source)
        except ScraperError as e:
            console.print(
                f"[red]Error:[/red] Failed to scrape {e.source_name}: {e.message}"
            )
            raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
