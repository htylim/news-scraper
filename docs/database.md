# Database

SQLite database with SQLAlchemy ORM and Alembic migrations.

## Location

`data/news_scraper.db`

## Setup

Create data directory and run migrations:

```bash
mkdir -p data
uv run alembic upgrade head
```

## Alembic Commands

### Apply Migrations

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Apply next migration only
uv run alembic upgrade +1
```

### Create Migration

```bash
# Auto-generate from model changes
uv run alembic revision --autogenerate -m "description"

# Empty migration (manual)
uv run alembic revision -m "description"
```

### Rollback

```bash
# Rollback last migration
uv run alembic downgrade -1

# Rollback to specific revision
uv run alembic downgrade <revision_id>

# Rollback all migrations
uv run alembic downgrade base
```

### Status

```bash
# Show current revision
uv run alembic current

# Show migration history
uv run alembic history

# Show pending migrations
uv run alembic history --indicate-current
```
