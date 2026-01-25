# News Scraper Project

CLI application for scraping news articles from URLs.

## Project documentation

**Always update documents as project evolves**

- [Project Structure](./project-structure.md)
- [Libraries](./libraries.md)
- [Architecture Decisions](./architecture.md)
- [Coding Guidelines](./coding-guidelines.md)
- [Testing Guidelines](./testing-guidelines.md)
- [Documentation Guidelines](./documentation-guidelines.md)
- [Database](./database.md)
- [Models Guidelines](./models-guidelines.md)
- [Queries](./queries.md)
- [Learnings](./learnings.md)

## Current State

Basic CLI scaffold with Typer. Scraping infrastructure implemented:

- **Browser automation** (`browser.py`): Headless Chrome via Playwright with custom User-Agent, renders JavaScript-heavy pages
- **Scraping logic** (`scraper.py`): Fetches source URLs using the browser module, outputs rendered HTML

## Entry Point

```
src/news_scraper/cli.py
```
