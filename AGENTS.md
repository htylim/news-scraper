- **Follow best practices** - Use industry-standard patterns and conventions.
- **Run tests** - `uv run pytest` after any code change.
- **Run pre-commit** - `uv run pre-commit run --all-files` before completing work.
- **Update documentation** - Keep this file and docs in sync as code changes.
- **Update `./docs/learnings.md`** - With discovered patterns for future iterations.
- **Code in spec files (`./docs/specs/*`) are reference code** - don't use it blindly.
- **`./docs/specs/*` can be ambiguous or incomplete** - Always ask clarifying questions.

## Project Documents

**Always update documents as project evolves**

- [Project Structure](./docs/project-structure.md)
- [Libraries](./docs/libraries.md)
- [Architecture Decisions](./docs/architecture.md)
- [Coding Instructions](./docs/coding.md)
- [Testing Instructions](./docs/testing.md)
- [Documentation Instructions](./docs/writing.md)
- [Database](./docs/database.md)
- [Models Standards](./docs/models.md)
- [Queries](./docs/queries.md)
- [Learnings](./docs/learnings.md)

## Current State

Basic CLI scaffold with Typer. Scraping infrastructure implemented:

- **Browser automation** (`browser.py`): Headless Chrome via Playwright with custom User-Agent, renders JavaScript-heavy pages
- **Scraping logic** (`scraper.py`): Fetches source URLs using the browser module, outputs rendered HTML

## Entry Point

```
src/news_scraper/cli.py
```
