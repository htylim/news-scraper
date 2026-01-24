# News Scraper CLI - Requirements Document

## Project Overview
A professional Python CLI application for scraping news articles from URLs. This project follows industry best practices for Python CLI development, packaging, and distribution.

## Python Version
- **Python 3.12** - Required Python version (latest stable as of 2025)
- Use the latest stable micro-release (e.g., 3.12.x) for security and bug fixes

## Dependency Version Policy
- **Always use the latest stable version** of all dependencies unless there is an explicit reason not to
- Pin versions only when necessary (e.g., breaking changes, compatibility issues)
- Document any version constraints and their reasons

## Phase 1: Basic CLI Foundation

### Core Functionality
- Accept a URL as a command-line argument
- Print the URL to stdout
- Basic error handling for invalid inputs

### Technical Stack

#### CLI Framework
- **Typer** - Modern CLI framework built on Click, leveraging Python type hints
  - Type-safe argument parsing
  - Automatic help generation
  - Better developer experience than raw argparse

#### Testing
- **pytest** - Testing framework
- **pytest-cov** - Code coverage reporting

#### Code Quality Tools
- **ruff** - Fast Python linter and formatter (replaces black + flake8)
- **mypy** - Static type checker
- **pre-commit** - Git hooks for automated quality checks

##### Pre-commit Configuration
- **Pre-commit hooks must only contain ruff and mypy** - No other hooks should be added
- **Use latest stable versions** - Always use the latest stable versions of ruff-pre-commit and mirrors-mypy repositories
- **Version pinning requirement** - The exact versions used in `.pre-commit-config.yaml` must be pinned (using `==`) in `pyproject.toml` under `[project.optional-dependencies.dev]`
- **Version synchronization** - When updating pre-commit hook versions, both `.pre-commit-config.yaml` and `pyproject.toml` must be updated together to maintain consistency
- **Rationale** - This ensures identical behavior between automated pre-commit hooks and manual tool execution, preventing version drift and inconsistent results

#### Terminal Output
- **rich** - Beautiful terminal output library
  - Colored output
  - Progress bars
  - Tables
  - Better UX than plain print statements

#### Logging
- **structlog** - Structured logging library
  - Better than standard logging for production applications
  - Structured output (JSON, key-value pairs)
  - Better context binding and performance
  - Easier to integrate with log aggregation systems

#### Package Management
- **uv** - Fast Python package installer and resolver (written in Rust)
  - Replaces pip, venv, and virtualenv
  - Much faster than traditional pip
  - Handles virtual environment management
  - Can manage project dependencies via pyproject.toml
  - Similar to poetry but faster

### Project Structure

```
news-scraper/
├── src/
│   └── news_scraper/
│       ├── __init__.py          # Package initialization, version
│       ├── cli.py               # CLI entry point
│       └── __main__.py          # Allows: python -m news_scraper
├── tests/
│   ├── __init__.py
│   └── test_cli.py              # CLI tests
├── docs/
│   ├── requirements.md          # This file
│   ├── architecture.md          # Architecture decisions (ADRs)
│   └── learnings.md             # Notes and learnings
├── .gitignore                   # Python gitignore
├── .pre-commit-config.yaml      # Pre-commit hooks config
├── pyproject.toml               # Modern Python packaging config (dependencies managed here)
├── README.md                    # User-facing documentation
└── .venv/                       # Virtual environment (created by uv, gitignored)
```

### Packaging & Installation

#### Prerequisites
- **Python 3.12** - Required Python version (latest stable)
- Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Or via pip: `pip install uv`
  - Or via homebrew: `brew install uv`

#### Development Installation
```bash
# Create virtual environment and install package in editable mode
uv pip install -e ".[dev]"

# Or use uv's project management (if using uv project features)
uv sync
```

#### Production Installation
```bash
# Using uv
uv pip install .

# Or build wheel and install
uv build
uv pip install dist/news_scraper-*.whl

# Traditional pip still works
pip install .
```

#### Entry Points
- CLI command: `news-scraper` (or `news-scraper-cli`)
- Accessible via: `python -m news_scraper`

### Key Features to Implement

1. **CLI Command Structure**
   - Command: `news-scraper <url>`
   - Options: `--version`, `--verbose`, `--help`
   - URL validation

2. **Error Handling**
   - Invalid URL format
   - Network errors (for future)
   - Custom exception classes

3. **Version Management**
   - `__version__` in `__init__.py`
   - Accessible via `--version` flag
   - Semantic versioning

4. **Type Hints**
   - Full type coverage
   - mypy strict mode compliance

5. **Code Quality**
   - Ruff for linting/formatting
   - mypy for type checking
   - Pre-commit hooks for automation
   - pytest with coverage

6. **Documentation**
   - README.md with installation and usage
   - Docstrings (Google style)
   - Type hints as inline documentation

### Development Workflow

1. **Setup**
   ```bash
   # Create virtual environment (uv automatically creates .venv)
   uv venv
   
   # Activate virtual environment
   source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
   
   # Install package in editable mode with dev dependencies
   uv pip install -e ".[dev]"
   
   # Install pre-commit hooks
   pre-commit install
   ```

2. **Development**
   - Write code with type hints
   - Run tests: `pytest` or `uv run pytest`
   - Check types: `mypy src/` or `uv run mypy src/`
   - Format/lint: `ruff check .` and `ruff format .` or `uv run ruff check .`
   - Add dependencies: `uv pip install <package>` or edit `pyproject.toml` and run `uv pip install -e ".[dev]"`

3. **Pre-commit**
   - Automatically runs ruff and mypy before commits
   - Ensures code quality
   - Only ruff and mypy hooks are configured (see Pre-commit Configuration section)
   - Versions are synchronized between `.pre-commit-config.yaml` and `pyproject.toml`

4. **uv Benefits**
   - Much faster than pip (10-100x faster)
   - Automatic virtual environment management
   - Better dependency resolution
   - Can run commands in venv: `uv run pytest` (no need to activate)

### Dependencies

**Note:** All dependencies use the latest stable version unless explicitly pinned for a documented reason.

#### Runtime Dependencies
- typer (latest stable)
- rich (latest stable)
- structlog (latest stable)

#### Development Dependencies
- pytest (latest stable)
- pytest-cov (latest stable)
- ruff (pinned to match pre-commit version - see Pre-commit Configuration)
- mypy (pinned to match pre-commit version - see Pre-commit Configuration)
- pre-commit (latest stable)

### Future Considerations (Not in Phase 1)

- Actual web scraping functionality
- Multiple output formats (JSON, CSV, etc.)
- Configuration files
- Caching mechanisms
- Rate limiting
- CI/CD pipeline
- Docker containerization

## Success Criteria

- [x] CLI accepts URL argument
- [x] Prints URL to stdout
- [x] Proper error handling
- [x] Installable via uv/pip
- [x] Type hints throughout
- [x] Tests passing
- [x] Ruff and mypy passing
- [x] Pre-commit hooks working
- [x] Documentation complete
- [x] uv setup and workflow documented