# S002: Database Scaffolding

Add SQLAlchemy and Alembic for database persistence with SQLite.

## Goal

Set up the foundational database infrastructure: ORM, migrations, configuration, and an initial model.

## Libraries

### Runtime Dependencies

- **SQLAlchemy 2.0.46** - ORM with native type hints support
  - Uses `Mapped` and `mapped_column()` for type-safe models
  - No mypy plugin needed (deprecated, incompatible with mypy 1.11+)
- **Alembic 1.18.1** - Database migrations
  - Compatible with SQLAlchemy 2.0+
  - Autogenerate support for schema changes

### Database

- **SQLite** - Lightweight, file-based database
  - No additional drivers needed (built into Python)
  - Location: `data/news_scraper.db`

## Deliverables

### 1. Configuration Module

**File:** `src/news_scraper/config.py`

Central configuration for the project.

```python
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Database
DATABASE_URL = f"sqlite:///{DATA_DIR}/news_scraper.db"
```

### 2. Database Module

**Directory:** `src/news_scraper/db/`

```
src/news_scraper/db/
├── __init__.py      # Exports engine, SessionLocal, get_session, Base
├── base.py          # DeclarativeBase with common mixins
├── session.py       # Engine and session management
└── models/
    ├── __init__.py  # Exports all models
    └── source.py    # Source model
```

#### base.py

Declarative base with timestamp mixin.

```python
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

Notes:
- `server_default` - Database evaluates `now()` server-side (consistent timestamps)
- `onupdate` - Python/ORM-side; triggers on `session.commit()` when object is dirty

#### session.py

Engine and session management.

```python
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from news_scraper.config import DATABASE_URL, DATA_DIR

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for database sessions.
    
    Usage:
        with get_session() as session:
            session.add(obj)
            session.commit()
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

Notes:
- `SessionLocal` is the factory (named to avoid shadowing `sqlalchemy.orm.Session`)
- `get_session()` context manager ensures proper cleanup
- Data directory is created on module import

### 3. Source Model

**File:** `src/news_scraper/db/models/source.py`

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from news_scraper.db.base import Base, TimestampMixin


class Source(TimestampMixin, Base):
    """News source configuration."""
    
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, name={self.name!r})>"
```

### 4. Alembic Setup

**Directory:** `alembic/` (project root)

```
alembic/
├── env.py           # Migration environment config
├── script.py.mako   # Migration template
└── versions/        # Migration files
```

**File:** `alembic.ini` (project root)

Standard Alembic config with:
- `sqlalchemy.url` pointing to config's DATABASE_URL
- Script location: `alembic`

#### env.py modifications

- Import `Base` from `news_scraper.db.base`
- Import all models to register them with Base
- Set `target_metadata = Base.metadata`
- Use `DATABASE_URL` from config

### 5. Initial Migration

Create initial migration for the `sources` table.

```bash
alembic revision --autogenerate -m "create sources table"
```

### 6. Documentation

#### docs/database.md

Alembic commands reference:

```markdown
# Database

SQLite database with SQLAlchemy ORM and Alembic migrations.

## Location

`data/news_scraper.db`

## Setup

Create data directory and run migrations:

```bash
mkdir -p data
alembic upgrade head
```

## Alembic Commands

### Apply Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply next migration only
alembic upgrade +1
```

### Create Migration

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "description"

# Empty migration (manual)
alembic revision -m "description"
```

### Rollback

```bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

### Status

```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic history --indicate-current
```
```

#### docs/models-guidelines.md

```markdown
# Models Guidelines

Standards for creating SQLAlchemy models.

## Required Fields

All models must include:
- `id` - Auto-increment primary key
- `created_at` - Timestamp, set on insert (via `TimestampMixin`)
- `updated_at` - Timestamp, auto-updates on modification (via `TimestampMixin`)

Use `TimestampMixin` from `news_scraper.db.base`.

## Required Methods

- `__repr__` - Return readable string for debugging (include `id` and a key identifier)

## Type Annotations

- Use `Mapped[T]` for all columns
- Use `mapped_column()` instead of `Column()`
- Use `str | None` for optional fields (not `Optional[str]`)

## Naming

- Table names: lowercase, plural, snake_case (`sources`, `news_articles`)
- Model classes: PascalCase, singular (`Source`, `NewsArticle`)

## Constraints

- Always specify `nullable` explicitly
- Add `unique=True` where business logic requires it
- Use appropriate `String` lengths

## Session Usage

Use the `get_session()` context manager:

```python
from news_scraper.db import get_session

with get_session() as session:
    source = Source(name="Example", url="https://example.com")
    session.add(source)
    session.commit()
```

## Example

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from news_scraper.db.base import Base, TimestampMixin


class MyModel(TimestampMixin, Base):
    __tablename__ = "my_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    optional_field: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<MyModel(id={self.id}, name={self.name!r})>"
```
```

### 7. MyPy Configuration

No plugin needed. SQLAlchemy 2.0's native typing works with mypy strict mode.

If needed, add override for Alembic (its types may be incomplete):

```toml
[[tool.mypy.overrides]]
module = ["alembic.*"]
ignore_missing_imports = true
```

### 8. Update Existing Documentation

#### pyproject.toml

Add to dependencies:
```toml
dependencies = [
    "typer",
    "rich",
    "structlog",
    "sqlalchemy>=2.0.46",
    "alembic>=1.18.1",
]
```

#### docs/project.md

Add link to database.md and models-guidelines.md.

#### docs/libraries.md

Add SQLAlchemy and Alembic to runtime dependencies.

#### docs/project-structure.md

Update structure to include:
- `src/news_scraper/config.py`
- `src/news_scraper/db/` directory
- `alembic/` directory
- `data/` directory

#### docs/architecture.md

Add ADR for database choice:
- ADR-007: Database - SQLite with SQLAlchemy
- ADR-008: Migrations - Alembic

### 9. Gitignore

Add to `.gitignore`:
```
# Database
data/*.db
```

Note: `data/.gitkeep` is committed to preserve directory structure.

## File Summary

New files:
- `src/news_scraper/config.py`
- `src/news_scraper/db/__init__.py`
- `src/news_scraper/db/base.py`
- `src/news_scraper/db/session.py`
- `src/news_scraper/db/models/__init__.py`
- `src/news_scraper/db/models/source.py`
- `alembic.ini`
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/.gitkeep`
- `docs/database.md`
- `docs/models-guidelines.md`
- `data/.gitkeep`
- `tests/conftest.py`
- `tests/db/__init__.py`
- `tests/db/test_models.py`

Updated files:
- `pyproject.toml`
- `docs/project.md`
- `docs/libraries.md`
- `docs/project-structure.md`
- `docs/architecture.md`
- `.gitignore`

## Testing

### Test Files

**File:** `tests/conftest.py` - Shared fixtures

```python
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from news_scraper.db.base import Base
from news_scraper.db.models import Source  # noqa: F401 - registers model


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """In-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
```

**File:** `tests/db/__init__.py` - Empty

**File:** `tests/db/test_models.py` - Model tests

```python
import pytest
from sqlalchemy.exc import IntegrityError

from news_scraper.db.models import Source


class TestSourceModel:
    """Tests for the Source model."""

    def test_create_source(self, db_session: Session) -> None:
        """Source can be created with required fields."""
        source = Source(name="Test News", url="https://test.com")
        db_session.add(source)
        db_session.commit()

        assert source.id is not None
        assert source.name == "Test News"
        assert source.url == "https://test.com"
        assert source.logo_url is None
        assert source.is_enabled is True

    def test_create_source_all_fields(self, db_session: Session) -> None:
        """Source can be created with all fields."""
        source = Source(
            name="Full News",
            url="https://full.com",
            logo_url="https://full.com/logo.png",
            is_enabled=False,
        )
        db_session.add(source)
        db_session.commit()

        assert source.logo_url == "https://full.com/logo.png"
        assert source.is_enabled is False

    def test_timestamps_set_on_create(self, db_session: Session) -> None:
        """created_at and updated_at are set on insert."""
        source = Source(name="Time News", url="https://time.com")
        db_session.add(source)
        db_session.commit()

        assert source.created_at is not None
        assert source.updated_at is not None

    def test_name_unique_constraint(self, db_session: Session) -> None:
        """Duplicate names are rejected."""
        source1 = Source(name="Unique", url="https://one.com")
        db_session.add(source1)
        db_session.commit()

        source2 = Source(name="Unique", url="https://two.com")
        db_session.add(source2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_url_unique_constraint(self, db_session: Session) -> None:
        """Duplicate URLs are rejected."""
        source1 = Source(name="First", url="https://same.com")
        db_session.add(source1)
        db_session.commit()

        source2 = Source(name="Second", url="https://same.com")
        db_session.add(source2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_repr(self, db_session: Session) -> None:
        """__repr__ returns readable string."""
        source = Source(name="Repr Test", url="https://repr.com")
        db_session.add(source)
        db_session.commit()

        assert "Repr Test" in repr(source)
        assert str(source.id) in repr(source)
```

### Test Guidelines

- Use in-memory SQLite (`sqlite:///:memory:`) for speed
- Each test gets fresh tables via fixture
- Test constraints (unique, nullable) with `pytest.raises(IntegrityError)`
- Rollback session in fixture after each test to isolate state

## Acceptance Criteria

- [ ] SQLAlchemy and Alembic installed and importable
- [ ] `config.py` with DATABASE_URL
- [ ] Database module with Base, SessionLocal, get_session, engine
- [ ] Source model with all fields, constraints, and `__repr__`
- [ ] TimestampMixin working (created_at, updated_at)
- [ ] Alembic initialized and configured
- [ ] Initial migration created and applies cleanly
- [ ] `alembic upgrade head` creates sources table
- [ ] `alembic downgrade -1` rolls back cleanly
- [ ] Source model tests pass (CRUD, constraints, timestamps)
- [ ] All tests pass (existing + new)
- [ ] mypy passes with strict mode
- [ ] ruff passes
- [ ] Documentation updated
