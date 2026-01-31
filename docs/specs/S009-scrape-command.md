# Goal
Add a dedicated `scrape` subcommand to the CLI so scraping is explicit and extensible. Running `news-scraper scrape` should scrape all enabled sources, while `news-scraper scrape <source_name> [<source_name> ...]` should scrape only the listed sources. This replaces the current root-level `--source/-s` flow.

# Problem / Context
The current CLI requires a `--source` option on the root command, which prevents a clean "scrape everything" workflow and makes future commands awkward. A subcommand aligns with common CLI conventions and clarifies intent.

# Deliverables
- Add `scrape` as a Typer subcommand in `src/news_scraper/cli.py`.
- Keep the root callback for global options only (`--verbose`, `--version`); it should no longer perform scraping.
- Define `scrape` usage as:
  - `news-scraper scrape` → scrape all enabled sources.
  - `news-scraper scrape <source_name> [<source_name> ...]` → scrape only the specified sources (one or many).
- Remove the root-level `--source/-s` option and any logic that requires it.
- Source selection behavior:
  - When one or more source names are provided:
    - Validate each with `validate_slug()`.
    - Deduplicate normalized names while preserving input order.
    - Look up each by normalized name; if any are missing or disabled, report them and exit non-zero without scraping.
  - When no source is provided, query all enabled sources (stable order, e.g., by name) and error if none exist.
- Multi-source execution behavior:
  - Iterate sources in order, call `scrape(source)` for each.
  - Print a clear per-source header before outputting results.
  - On `ScraperError`, print the error and continue with remaining sources.
  - Exit with code `1` if any source fails; otherwise exit `0`.
- Update CLI tests in `tests/test_cli.py` to reflect the new subcommand and behaviors (single source, multi-source, missing/disabled, and "all" mode).
- Update `docs/learnings.md` with new CLI patterns discovered during implementation.

Reference code in this spec is for clarity only; do not copy-paste blindly.

# Acceptance Criteria
- [ ] `news-scraper scrape` scrapes all enabled sources.
- [ ] `news-scraper scrape <source_name> [<source_name> ...]` scrapes only the specified sources.
- [ ] Missing/invalid/disabled sources return a clear error and non-zero exit code.
- [ ] Multi-source scrape continues after per-source failures and returns exit code `1` if any failed.
- [ ] Root command no longer accepts `--source/-s`.
- [ ] CLI tests updated/added to cover single-source and multi-source cases.
- [ ] `uv run pytest`
- [ ] `uv run pre-commit run --all-files`

# File Summary
- New: `docs/specs/S009-scrape-command.md`
- Update: `src/news_scraper/cli.py`
- Update: `tests/test_cli.py`
- Update: `docs/learnings.md`

# Open Questions / Resolved Decisions
- Resolved: Use positional source arguments on `scrape` (primary target arguments), not a `--source/-s` option.
