"""CLI module for news-scraper."""

from typing import Annotated

import typer
from rich.console import Console
from sqlalchemy import select

from news_scraper import __version__
from news_scraper.db import get_session
from news_scraper.db.models import Source
from news_scraper.logging import configure_logging, get_logger
from news_scraper.parsers import load_site_parsers
from news_scraper.scraper import ScraperError, print_scrape_result, scrape
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
    """A professional CLI for scraping news articles."""
    # Initialize logging once at startup
    configure_logging()
    log = get_logger()

    if verbose:
        log.debug("Verbose mode enabled")

    load_site_parsers()


@app.command(name="scrape")
def scrape_cmd(
    source_names: Annotated[
        list[str],
        typer.Argument(help="Source name(s) to scrape. If omitted, scrapes all enabled sources."),
    ] = [],
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose output")
    ] = False,
) -> None:
    """Scrape news from configured source(s).

    If no source names are provided, scrapes all enabled sources.
    If one or more source names are provided, scrapes only those sources.
    """
    log = get_logger()

    if verbose:
        log.debug("Verbose mode enabled")

    with get_session() as session:
        sources_to_scrape: list[Source] = []

        if source_names:
            # Validate and normalize all source names
            normalized_names: list[str] = []
            for source_name in source_names:
                try:
                    normalized = validate_slug(source_name, field_name="source")
                    normalized_names.append(normalized)
                except ValidationError as e:
                    log.error("Invalid source name", source=source_name, error=str(e))
                    console.print(f"[red]Error:[/red] {e.message}")
                    raise typer.Exit(code=1) from None

            # Deduplicate while preserving order
            seen: set[str] = set()
            unique_normalized: list[str] = []
            for name in normalized_names:
                if name not in seen:
                    seen.add(name)
                    unique_normalized.append(name)

            # Lookup sources
            missing_or_disabled: list[str] = []
            for normalized_name in unique_normalized:
                stmt = select(Source).where(Source.name == normalized_name)
                source = session.scalars(stmt).first()

                if source is None:
                    missing_or_disabled.append(normalized_name)
                    log.error("Source not found", source=normalized_name)
                elif not source.is_enabled:
                    missing_or_disabled.append(normalized_name)
                    log.error("Source is disabled", source=normalized_name)
                else:
                    sources_to_scrape.append(source)

            if missing_or_disabled:
                for name in missing_or_disabled:
                    console.print(f"[red]Error:[/red] Source not found or disabled: {name}")
                raise typer.Exit(code=1)
        else:
            # Query all enabled sources, ordered by name
            stmt = select(Source).where(Source.is_enabled == True).order_by(Source.name)
            sources_to_scrape = list(session.scalars(stmt).all())

            if not sources_to_scrape:
                console.print("[red]Error:[/red] No enabled sources found")
                raise typer.Exit(code=1)

        # Scrape each source
        has_failures = False
        for source in sources_to_scrape:
            console.print(f"\n[bold]Scraping {source.name}[/bold]")
            console.print("=" * 80)

            log.info("Scraping source", source=source.name)
            try:
                result = scrape(source)
                print_scrape_result(result)
            except ScraperError as e:
                has_failures = True
                console.print(
                    f"[red]Error:[/red] Failed to scrape {e.source_name}: {e.message}"
                )
                log.error("Scraping failed", source=e.source_name, error=e.message)

        if has_failures:
            raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
