# Cursor Cloud Environment Setup

Quick, repeatable setup steps for this repository on Cursor Cloud.

## Prereqs
- Use `python3` (the `python` alias may not exist).
- Install `uv` with `python3 -m pip` (binary may not be on PATH).

## Setup Steps
1. Install uv (user scope):
   ```
   python3 -m pip install --user uv
   ```

2. Create a local virtual environment:
   ```
   python3 -m uv venv .venv
   ```

3. Install project + dev dependencies into the venv:
   ```
   python3 -m uv pip install -e ".[dev]" --python .venv/bin/python
   ```

4. Run tests and pre-commit in the venv:
   ```
   python3 -m uv run --python .venv/bin/python pytest
   python3 -m uv run --python .venv/bin/python pre-commit run --all-files
   ```

## Troubleshooting
- `uv: command not found`: use `python3 -m uv ...` or add `~/.local/bin` to PATH.
- `pytest` not found: ensure step 3 ran successfully.
- `Permission denied` under `/usr/...`: avoid system installs; target the venv
  with `--python .venv/bin/python`.
