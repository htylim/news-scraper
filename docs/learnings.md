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
- Use `BaseParser` as the shared interface for site parsers; Protocol not needed
- Keep registry storing parser classes and returning instances for simple typing
- Deduplicate articles by URL using a set for O(1) lookup
- Combine nested `with` statements using parenthesized context managers (ruff SIM117)
- Always read/write HTML fixtures with `encoding="utf-8"` to preserve non-ASCII text
- BeautifulSoup `get_text(strip=True)` strips each text segment before joining; when a headline is split across siblings (e.g. `<span>Prefix. </span>Rest`), the trailing space in the first segment is removed, producing "Prefix.Rest". Use `get_text(strip=False)` and then `.strip()` on the full result to preserve internal spaces.

## Phase 5: Parser Architecture (S008)

- Favor `iter_article_elements()` over a single selector to avoid assumptions about site structure.
- Centralize parse loop in a base parser to standardize logging, dedupe, and position assignment.
- Use `resolve_url()` to normalize URLs consistently (strip query/fragment, enforce allowed hosts).
- Add direct unit tests for URL/srcset helpers to pin edge-case behavior (fragments, non-http schemes, root paths).
- Register parsers with a decorator and instantiate from classes in the registry.
- Load site parser modules during app initialization to avoid registry import side effects.

## Phase 6: CLI Scrape Command (S009)

- Prefer explicit subcommands for actions; keep root callback for global options only.
- Use an optional positional argument for the primary target; absence implies "all".

## Phase 7: Database Migrations

- Seed migrations should be idempotent via `INSERT ... WHERE NOT EXISTS` or `ON CONFLICT DO NOTHING`.
