# News Scraper CLI

A Python CLI application for scraping news articles from configured sources using headless browser automation.

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Chrome/Chromium browser (for Playwright)

## Installation

### Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv pip install .

# Install Playwright browsers
uv run playwright install chromium
```

### Using pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install .

# Install Playwright browsers
playwright install chromium
```

## Database Setup

The application uses SQLite for storing source configurations. Initialize the database:

```bash
mkdir -p data
uv run alembic upgrade head
```

## Usage

```bash
# Scrape articles from a configured source
news-scraper --source infobae
news-scraper -s infobae

# With verbose output
news-scraper --source infobae --verbose

# Show version
news-scraper --version

# Show help
news-scraper --help
```

### Running as a module

```bash
python -m news_scraper --source infobae
```

### Supported Sources

| Source   | Description                    |
|----------|--------------------------------|
| infobae  | Infobae news front page        |

## Development

### Setup

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install with dev dependencies
uv pip install -e ".[dev]"

# Install Playwright browsers
uv run playwright install chromium

# Install pre-commit hooks
pre-commit install

# Setup database
mkdir -p data
uv run alembic upgrade head
```

### Running Tests

```bash
# Run tests with coverage
uv run pytest

# Run tests without coverage
uv run pytest --no-cov
```

### Code Quality

```bash
# Lint and format
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy src/

# Run all checks (via pre-commit)
uv run pre-commit run --all-files
```

### Database Migrations

```bash
# Apply all migrations
uv run alembic upgrade head

# Create new migration from model changes
uv run alembic revision --autogenerate -m "description"

# Rollback last migration
uv run alembic downgrade -1

# Show migration status
uv run alembic current
```

## Project Structure

```
news-scraper/
├── src/news_scraper/         # Source code
│   ├── __init__.py           # Package version
│   ├── __main__.py           # python -m support
│   ├── cli.py                # CLI entry point (Typer)
│   ├── config.py             # Central configuration
│   ├── logging.py            # Structlog configuration
│   ├── browser.py            # Headless Chrome via Playwright
│   ├── scraper.py            # Scraping orchestration
│   ├── validation.py         # Input validation
│   ├── parsers/              # Site-specific HTML parsers
│   │   ├── __init__.py       # Parser registry
│   │   ├── base.py           # Parser protocol + Article model
│   │   └── infobae.py        # Infobae parser
│   └── db/                   # Database layer
│       ├── __init__.py       # Module exports
│       ├── base.py           # SQLAlchemy base + mixins
│       ├── session.py        # Engine and session management
│       └── models/           # ORM models
│           └── source.py     # Source model
├── alembic/                  # Database migrations
│   └── versions/             # Migration files
├── data/                     # SQLite database (gitignored)
├── tests/                    # Test suite
├── docs/                     # Documentation
│   ├── PROJECT.md            # Project overview
│   ├── architecture.md       # Architecture decisions
│   ├── database.md           # Database documentation
│   └── specs/                # Feature specifications
├── pyproject.toml            # Package configuration
├── alembic.ini               # Alembic configuration
└── .pre-commit-config.yaml   # Pre-commit hooks
```

## Tech Stack

- **CLI**: Typer with Rich for terminal output
- **Browser**: Playwright (headless Chromium)
- **HTML Parsing**: BeautifulSoup4 with lxml
- **Database**: SQLite with SQLAlchemy 2.0 ORM
- **Migrations**: Alembic
- **Logging**: structlog
- **Linting/Formatting**: Ruff
- **Type Checking**: mypy

## License

MIT
