# News Scraper CLI

A professional Python CLI application for scraping news articles from URLs.

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

### Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv pip install .
```

### Using pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
```

## Usage

```bash
# Basic usage
news-scraper https://example.com/article

# With verbose output
news-scraper --verbose https://example.com/article

# Show version
news-scraper --version

# Show help
news-scraper --help
```

### Running as a module

```bash
python -m news_scraper https://example.com/article
```

## Development

### Setup

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install with dev dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=news_scraper --cov-report=term-missing

# Or using uv
uv run pytest
```

### Code Quality

```bash
# Lint and format
ruff check .
ruff format .

# Type checking
mypy src/

# Run all checks (via pre-commit)
pre-commit run --all-files
```

## Project Structure

```
news-scraper/
├── src/
│   └── news_scraper/
│       ├── __init__.py      # Package initialization, version
│       ├── cli.py           # CLI entry point
│       └── __main__.py      # Allows: python -m news_scraper
├── tests/
│   └── test_cli.py          # CLI tests
├── docs/
│   ├── requirements.md      # Requirements document
│   ├── architecture.md      # Architecture decisions
│   └── learnings.md         # Notes and learnings
├── pyproject.toml           # Package configuration
├── .pre-commit-config.yaml  # Pre-commit hooks
└── README.md                # This file
```

## License

MIT
