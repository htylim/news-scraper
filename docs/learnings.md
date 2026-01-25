# Learnings

Notes, learnings, and insights gathered during development

**ALWAYS update this document with discovered patterns for future iterations.** 

## Phase 1: Basic CLI Foundation

- Initial project setup with modern Python tooling
- Established code quality standards with ruff and mypy

## Phase 2: Source-based CLI (S003)

- Use `@app.callback(invoke_without_command=True)` for main entry when CLI has options without subcommands
- SQLAlchemy `@validates` decorator runs on attribute assignment, before flush - use `ValueError` not custom exceptions
- Prefix unused function arguments with `_` to satisfy ruff ARG001/ARG002 rules
- Use `raise ... from None` in exception handlers that exit cleanly (ruff B904)
- Move structlog configuration to dedicated module - call once at startup, not at import time
- For CLI tests that patch `get_session`, ensure fixture is used even if test doesn't directly call DB
- Return `Any` type for structlog's `get_logger()` to satisfy mypy strict mode
- `__main__.py` should call `app()` not `main()` when using Typer callbacks
- Playwright `networkidle` can hang on sites with long-lived requests; prefer `domcontentloaded` and a best-effort `networkidle` wait

## Phase 3: Scraping Verification

- Use the browser agent (MCP cursor-ide-browser) to manually verify scraping results by navigating to the target URL and comparing visible content with scraper output

## Phase 4: HTML Parsing (S005)

- BeautifulSoup's `find(class_="foo")` performs partial CSS class matching - finds elements where "foo" is one of multiple classes
- Add type annotations for BeautifulSoup `get_text()` return values to satisfy mypy strict mode (e.g., `text: str = element.get_text(strip=True)`)
- Add mypy overrides for `bs4.*` and `lxml.*` modules (no stubs available)
- Use frozen dataclasses for immutable data transfer objects (Article) - provides hashability for deduplication
- Strategy pattern with Protocol enables adding new parsers without modifying existing code
- Use parser registry with instances (not classes) to avoid `type[Protocol]` typing issues
- Deduplicate articles by URL using a set for O(1) lookup
- Combine nested `with` statements using parenthesized context managers (ruff SIM117)