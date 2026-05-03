---
name: python-coding
category: development
description: Python coding conventions, testing, type hints, ruff, mypy, and best practices
---

# Python Coding Skill

## Conventions

- Use type hints on all public function signatures and return types
- Follow PEP 8 naming: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE` for constants
- Prefer `pathlib.Path` over `os.path` for all file operations
- Use f-strings for string formatting (not `.format()` or `%`)
- Keep functions under 50 lines; extract helpers for clarity
- Use `|` for union types (`str | None`) not `Optional[str]` (Python 3.10+)
- Prefer dataclasses or named tuples over plain dicts for structured data

## Testing

- Use `pytest` for all tests — never `unittest`
- Name test files `test_*.py`, test functions `test_<what>_<when>`
- Use descriptive names: `test_read_file_returns_error_when_missing`
- Run `pytest -v` before declaring any task complete
- Use `tmp_path` fixture (built into pytest) for temporary files — not `tempfile.mkdtemp()`
- Test error paths, not just happy paths
- One assertion concept per test; use multiple `assert` statements only when they test the same thing

## Virtual Environments

- Always use a virtual environment (`.venv/`)
- Create: `python3 -m venv .venv`
- Activate: `source .venv/bin/activate`
- Install editable with dev deps: `pip install -e ".[dev]"`
- Never run `pip install` globally

## Common Commands

```bash
# Full CI check (run before declaring done)
ruff check . && mypy nova/ && pytest

# Lint
ruff check .

# Auto-fix lint
ruff check --fix .

# Format
ruff format .

# Type check
mypy nova/

# Run tests verbosely
pytest -v

# Run a single test
pytest tests/test_foo.py::test_bar -v

# Run tests matching a keyword
pytest -k "search" -v
```

## Error Handling

- Catch specific exceptions, not bare `except Exception`
- Return error strings from tool handlers — never raise
- Log errors with `logger.error("...", exc_info=True)` for unexpected failures
- Use `try/except` only around the code that can actually fail

## Imports

- Standard library first, then third-party, then local — separated by blank lines
- Never use `from module import *`
- Prefer absolute imports over relative for clarity
- Move heavy imports inside functions if they're only needed conditionally

## Pitfalls

- Don't commit `__pycache__/`, `.venv/`, `*.pyc`, or `.mypy_cache/`
- Don't use mutable default arguments: `def f(x=[])` — use `def f(x=None)` and set inside
- Don't shadow built-ins: avoid naming variables `list`, `dict`, `type`, `id`, `input`
- Don't use `os.system()` — use `subprocess.run()` with `check=True`
- Always verify file edits by reading back the file after writing
