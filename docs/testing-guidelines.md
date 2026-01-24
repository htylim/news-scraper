# Testing Guidelines

Rules and instructions for running tests.

## Policy

- Always run unit tests before committing

## Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=news_scraper --cov-report=term-missing

# Using uv
uv run pytest
```

## Test Location

Tests live in `tests/` directory, mirroring `src/news_scraper/` structure.
