---
name: python-coding
category: development
description: Python coding conventions, testing, and best practices
---

# Python Coding Skill

## Conventions

- Use type hints on all function signatures
- Follow PEP 8 naming: `snake_case` for functions/variables, `PascalCase` for classes
- Prefer `pathlib.Path` over `os.path`
- Use f-strings for string formatting
- Keep functions under 50 lines; extract helpers for clarity

## Testing

- Use `pytest` for all tests
- Name test files `test_*.py` or `*_test.py`
- Use descriptive test names: `test_function_does_thing_when_condition`
- Run tests with `pytest -v` before declaring work complete

## Virtual Environments

- Always use a virtual environment (`.venv/`)
- Create with `python3 -m venv .venv`
- Activate with `source .venv/bin/activate`
- Install deps with `pip install -e .` or `pip install -r requirements.txt`

## Common Commands

```bash
# Run tests
pytest -v

# Lint with ruff
ruff check .

# Auto-fix lint issues
ruff check --fix .

# Format with ruff
ruff format .

# Type check with mypy
mypy .
```

## Pitfalls

- Don't use `pip install` globally — always use a venv
- Don't commit `__pycache__/`, `.venv/`, or `*.pyc` files
- Don't use `from module import *` — be explicit about imports
- When editing files, always verify the edit worked by reading back the file
