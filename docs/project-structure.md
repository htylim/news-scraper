# Project Structure

Overview of directory layout and file organization.

```
news-scraper/
├── src/news_scraper/     # Source code
│   ├── __init__.py       # Package version
│   ├── __main__.py       # python -m support
│   └── cli.py            # CLI entry point
├── tests/                # Test files
├── docs/                 # Documentation
│   └── specs/            # Feature specs
└── pyproject.toml        # Package config
```

## Layout

Uses `src` layout - source code isolated in `src/` directory.

## Configuration

All config in `pyproject.toml`:
- Dependencies
- Tool settings (ruff, mypy, pytest)
- Build system (hatchling)
