# Queries

SQLAlchemy 2.0 query patterns. **Do not use legacy `session.query()` API.**

## Basic Queries

```python
from sqlalchemy import select

from news_scraper.db import get_session
from news_scraper.db.models import Source

with get_session() as session:
    # Single result
    stmt = select(Source).where(Source.name == "example")
    source = session.scalars(stmt).first()

    # All results
    stmt = select(Source).where(Source.is_enabled.is_(True))
    sources = session.scalars(stmt).all()

    # With ordering
    stmt = select(Source).order_by(Source.name)
    sources = session.scalars(stmt).all()
```

## Legacy Style (DO NOT USE)

```python
# WRONG - deprecated
source = session.query(Source).filter(Source.name == "example").first()
```

## Quick Reference

- Build query: `select(Model).where(...)`
- Execute: `session.scalars(stmt)`
- Filter: `.where(Model.col == val)`
- Get one: `.first()` or `.one()`
- Get all: `.all()`
