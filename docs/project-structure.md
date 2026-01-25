# Project Structure

Overview of directory layout and file organization.

```
news-scraper/
├── src/news_scraper/     # Source code
│   ├── __init__.py       # Package version
│   ├── __main__.py       # python -m support
│   ├── cli.py            # CLI entry point
│   ├── config.py         # Central configuration
│   ├── logging.py        # Structlog configuration
│   ├── scraper.py        # Scraper module
│   ├── validation.py     # Input validation utilities
│   ├── parsers/          # Site-specific HTML parsers
│   │   ├── __init__.py   # Parser registry
│   │   ├── base.py       # Parser protocol + Article model
│   │   └── infobae.py    # Infobae parser implementation
│   └── db/               # Database module
│       ├── __init__.py   # Module exports
│       ├── base.py       # DeclarativeBase + mixins
│       ├── session.py    # Engine and session management
│       └── models/       # ORM models
│           ├── __init__.py
│           └── source.py
├── alembic/              # Database migrations
│   ├── env.py            # Migration environment
│   ├── script.py.mako    # Migration template
│   └── versions/         # Migration files
├── data/                 # SQLite database (gitignored)
├── tests/                # Test files
├── docs/                 # Documentation
│   └── specs/            # Feature specs
├── alembic.ini           # Alembic config
└── pyproject.toml        # Package config
```

## Layout

Uses `src` layout - source code isolated in `src/` directory.

## Configuration

All config in `pyproject.toml`:
- Dependencies
- Tool settings (ruff, mypy, pytest)
- Build system (hatchling)
