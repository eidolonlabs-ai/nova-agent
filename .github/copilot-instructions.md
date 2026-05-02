# Nova Agent - Copilot Instructions

> **Repository:** https://github.com/eidolonlabs-ai/nova-agent
> **Organization:** Eidolon Labs LLC

## Project Overview
Nova Agent is a minimalist personal AI agent with explicit token budgets and smart context management.

## Architecture
- **nova/** - Main package
  - `agent.py` - Main agent loop with OpenRouter API integration
  - `config.py` - Configuration loading from YAML
  - `context.py` - Context file discovery with budgets and truncation
  - `memory.py` - Simple file-based memory system
  - `prompt.py` - System prompt assembly with mode gating
  - `session.py` - SQLite session storage with FTS5
  - `skills.py` - Skill discovery and loading
  - `tokens.py` - Token estimation utilities
  - `tools/` - Tool registry and built-in tools
    - `registry.py` - Central tool registry
    - `terminal.py` - Shell command execution
    - `file_ops.py` - File read/write/patch
    - `web.py` - Web search (placeholder)
  - `cli.py` - CLI entry point

## Key Design Principles
1. **Explicit token budgets** at every layer (system prompt, skills, context files, tool results)
2. **Two-tier tool descriptions** - compact list in prompt + JSON schemas to API
3. **Head/tail truncation** (70/20 ratio) for context files
4. **Prompt mode gating** - full/minimal/none for different agent types
5. **Prompt injection scanning** for security

## Development Commands
- Lint: `ruff check .`
- Auto-fix: `ruff check --fix .`
- Type check: `mypy nova/`
- Test: `pytest`
- Full CI check: `ruff check . && mypy nova/ && pytest`
- Run: `nova chat` or `nova ask "question"`

## Code Quality Standards
- **Type hints**: All public functions should have type annotations. Run `mypy nova/` to verify.
- **Linting**: Code must pass `ruff check .` with no errors.
- **Tests**: All 101 tests must pass. New features should include tests.
- **Test structure**: Tests use dependency injection — pass mock `http_client`, `session_store`, and `memory_store` to `NovaAgent` for isolated testing.
- **Test files**: `tests/test_agent.py`, `tests/test_config.py`, `tests/test_context.py`, `tests/test_cli.py`, `tests/test_memory.py`, `tests/test_model_metadata.py`, `tests/test_prompt.py`, `tests/test_registry.py`, `tests/test_session.py`, `tests/test_skills.py`, `tests/test_tokens.py`, `tests/test_tools.py`

## Configuration
Copy `config.yaml.example` to `config.yaml` and set your OpenRouter API key.

## Project Status
- All 101 tests passing
- Linting clean (ruff)
- Type checking clean (mypy — 0 errors in 20 files)
- CLI functional (chat, ask, sessions, reset)
- 10 tools available (terminal, read_file, write_file, patch_file, search_files, web_search, skills_list, skill_view, skill_manage, memory)
