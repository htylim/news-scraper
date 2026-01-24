# Architecture Decision Records

Log of architectural decisions and their rationale.

## ADR-001: CLI Framework - Typer

**Status:** Accepted

**Context:** Need a CLI framework for building the news-scraper command-line interface.

**Decision:** Use Typer.

**Rationale:**
- Built on Click with modern Python type hints
- Automatic help generation from type annotations
- Excellent developer experience
- Well-maintained by the FastAPI author

## ADR-002: Package Manager - uv

**Status:** Accepted

**Context:** Need a tool for dependency management and virtual environment handling.

**Decision:** Use uv.

**Rationale:**
- 10-100x faster than pip
- Written in Rust for performance
- Handles venv creation and dependency resolution
- Compatible with pyproject.toml standard

## ADR-003: Linting and Formatting - Ruff

**Status:** Accepted

**Context:** Need tools for code formatting and linting.

**Decision:** Use Ruff for both linting and formatting.

**Rationale:**
- Single tool replaces black + flake8 + isort
- Extremely fast (written in Rust)
- Comprehensive rule set
- Active development by Astral

## ADR-004: Logging - structlog

**Status:** Accepted

**Context:** Need a logging solution for the application.

**Decision:** Use structlog.

**Rationale:**
- Structured logging (JSON, key-value pairs)
- Better than standard logging for production
- Easy integration with log aggregation systems
- Good performance

## ADR-005: Terminal Output - Rich

**Status:** Accepted

**Context:** Need to provide user-friendly terminal output.

**Decision:** Use Rich.

**Rationale:**
- Beautiful terminal output with colors
- Tables, progress bars, syntax highlighting
- Works well with Typer
- Improves user experience

## ADR-006: Project Structure - src Layout

**Status:** Accepted

**Context:** Need to decide on project layout.

**Decision:** Use src layout (`src/news_scraper/`).

**Rationale:**
- Prevents accidental imports of uninstalled package
- Industry standard for distributable packages
- Clear separation of source and tests
- Better compatibility with packaging tools

## ADR-007: Database - SQLite with SQLAlchemy

**Status:** Accepted

**Context:** Need persistent storage for news sources and scraped articles.

**Decision:** Use SQLite with SQLAlchemy 2.0 ORM.

**Rationale:**
- SQLite: Zero configuration, file-based, built into Python
- SQLAlchemy 2.0: Native type hints with `Mapped` and `mapped_column()`
- No external database server required
- Easy to backup (single file)
- Sufficient for CLI application workload

## ADR-008: Migrations - Alembic

**Status:** Accepted

**Context:** Need schema versioning and migration management.

**Decision:** Use Alembic for database migrations.

**Rationale:**
- Official SQLAlchemy migration tool
- Autogenerate support detects model changes
- Supports upgrade and downgrade paths
- Industry standard for SQLAlchemy projects
