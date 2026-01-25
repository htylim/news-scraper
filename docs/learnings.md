# Learnings

Notes, learnings, and insights gathered during development

**ALWAYS update this document with discovered patterns for future iterations.** 

## Phase 1: Basic CLI Foundation

- Initial project setup with modern Python tooling
- Established code quality standards with ruff and mypy

## Phase 2: Source-based CLI (S003)

- Use `@app.callback(invoke_without_command=True)` for main entry when CLI has options without subcommands
- SQLAlchemy `@validates` decorator runs on attribute assignment, before flush - use `ValueError` not custom exceptions
- Prefix unused function arguments with `_` to satisfy ruff ARG001/ARG002 rules
- Use `raise ... from None` in exception handlers that exit cleanly (ruff B904)
- Move structlog configuration to dedicated module - call once at startup, not at import time
- For CLI tests that patch `get_session`, ensure fixture is used even if test doesn't directly call DB
- Return `Any` type for structlog's `get_logger()` to satisfy mypy strict mode
- `__main__.py` should call `app()` not `main()` when using Typer callbacks
