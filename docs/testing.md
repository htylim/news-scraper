# Testing Rules and Instructions

- **Always** run unit tests before committing
- Tests live in `tests/` directory, mirroring `src/news_scraper/` structure.
- Include positive and negative test scenarios.
- Make sure test code actually tests the scenario the test says it does.


## Running instructions

```bash
# Run all tests
pytest

# With coverage
pytest --cov=news_scraper --cov-report=term-missing

# Using uv
uv run pytest
```

