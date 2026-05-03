# Nova Agent — Claude Code Instructions

**Repository:** https://github.com/eidolonlabs-ai/nova-agent  
**Organization:** Eidolon Labs LLC

## Overview

Nova Agent is a minimalist personal AI agent with explicit token budgets and smart context management. It's designed to run locally with full control over model selection, API keys, and execution.

## Architecture

**Main package:** `nova/`

- `agent.py` — Main agent loop with OpenRouter API, streaming, tool calling, history truncation
- `cli.py` — CLI entry point (chat, ask, sessions, reset commands)
- `config.py` — YAML config loading with env var resolution, deep merge
- `context.py` — Context file discovery with budgets, head/tail truncation, injection scanning
- `memory.py` — File-based memory store with LRU eviction
- `model_metadata.py` — Model context window sizes for 20+ OpenRouter models
- `prompt.py` — System prompt assembly with mode gating (full/minimal/none)
- `session.py` — SQLite session storage with FTS5 full-text search
- `skills.py` — Skill discovery, YAML frontmatter parsing, XML-style prompt generation
- `tokens.py` — Token estimation via tiktoken with character fallback
- `tools/` — Tool registry and built-in tools
  - `registry.py` — Central tool registry with auto-discovery
  - `terminal.py` — Shell command execution with timeout and output truncation
  - `file_ops.py` — read_file, write_file, patch_file tools
  - `search_files.py` — Grep/regex search across project files
  - `web.py` — Bing RSS web search (zero dependencies, zero API key)
  - `skills_tool.py` — skills_list, skill_view, skill_manage tools
  - `memory_tool.py` — memory tool (add/search/delete/clear)

## Key Design Principles

1. **Explicit token budgets** at every layer (system prompt, skills, context files, tool results)
2. **Two-tier tool descriptions** — compact list in prompt + JSON schemas to API
3. **Head/tail truncation** (70/20 ratio) for context files to preserve structure
4. **Prompt mode gating** — full/minimal/none for different agent types
5. **Prompt injection scanning** for security

## Development Workflow

### Installation

```bash
# Create and activate venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Essential Commands

```bash
# Linting & formatting
ruff check .              # Check for issues
ruff check --fix .        # Auto-fix

# Type checking
mypy nova/

# Testing
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest --cov=nova         # Coverage report

# Full CI check
ruff check . && mypy nova/ && pytest
```

### Running the Agent

```bash
nova chat                 # Interactive chat
nova ask "question"       # Single question
nova sessions             # List sessions
nova reset                # Reset session state
```

## Code Quality Standards

**Type hints:** All public functions require type annotations. Verify with `mypy nova/` (0 errors in 20 files).

**Linting:** Code must pass `ruff check .` with no errors.

**Tests:** All 101 tests must pass.
- Test coverage baseline: CLI 82%, sessions/file_ops 91–100%
- Use dependency injection: pass mock `http_client`, `session_store`, and `memory_store` to `NovaAgent`
- Test files live in `tests/` with names matching source modules (e.g., `tests/test_agent.py` for `nova/agent.py`)
- New features should include tests

**Code style guidelines:**
- Default to no comments; only add when the *why* is non-obvious
- Don't explain what code does — well-named identifiers already do that
- No docstrings unless required by a framework
- Prefer editing existing files to creating new ones
- Avoid backwards-compatibility hacks; delete unused code cleanly

## Configuration

1. Copy `config.yaml.example` to `config.yaml`
2. Set your OpenRouter API key: `OPENROUTER_API_KEY=...`
3. Optionally customize model, max_tokens, temperature, system_prompt_mode

## Testing Notes

- Tests use `pytest` with fixtures in `conftest.py`
- Mock HTTP client, session store, and memory store for isolation
- Full CI check: `ruff check . && mypy nova/ && pytest`
- Coverage target: 80%+ for new code

## Current Status

✅ All 101 tests passing  
✅ Linting clean (ruff)  
✅ Type checking clean (mypy)  
✅ CLI functional (chat, ask, sessions, reset)  
✅ 10 tools available (terminal, read_file, write_file, patch_file, search_files, web_search, skills_list, skill_view, skill_manage, memory)

## Commit Message Convention

Use conventional commit format:

```
<type>: <subject>

<body (optional)>
```

**Types:** `feat` (new feature), `fix` (bug fix), `docs` (docs), `test` (test changes), `refactor` (code refactoring), `chore` (maintenance)

Examples:
- `feat: add web_search tool`
- `fix: handle empty context files gracefully`
- `test: expand CLI coverage to 82%`

## Feature Development

**Adding tools:** See [CONTRIBUTING.md](CONTRIBUTING.md#adding-tools) for the tool creation workflow (schema, handler, registration, tests).

**Adding skills:** See [docs/creating-skills.md](docs/creating-skills.md) for skill format and examples.

**Full contribution guidelines:** See [CONTRIBUTING.md](CONTRIBUTING.md).

## Working in Worktrees

When you create or enter a worktree, make sure to:
1. Set up the venv: `python3 -m venv .venv`
2. Install: `.venv/bin/pip install -e ".[dev]"`
3. Run tests to ensure isolation: `.venv/bin/pytest`

Use `.venv/bin/python`, `.venv/bin/pytest`, and `.venv/bin/ruff` — never global python3 or pytest.
