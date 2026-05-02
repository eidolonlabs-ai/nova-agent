# Nova Agent - Copilot Instructions

> **Repository:** https://github.com/eidolonlabs-ai/nova-agent
> **Organization:** Eidolon Labs LLC

## Project Overview
Nova Agent is a minimalist personal AI agent with explicit token budgets and smart context management.

## Architecture
- **nova/** - Main package
  - `agent.py` - Main agent loop with OpenRouter API, streaming, tool calling, history truncation
  - `cli.py` - CLI entry point (chat, ask, sessions, reset commands)
  - `config.py` - YAML config loading with env var resolution, deep merge
  - `context.py` - Context file discovery with budgets, head/tail truncation, injection scanning
  - `memory.py` - File-based memory store with LRU eviction
  - `model_metadata.py` - Model context window sizes for 20+ OpenRouter models
  - `prompt.py` - System prompt assembly with mode gating (full/minimal/none)
  - `session.py` - SQLite session storage with FTS5 full-text search
  - `skills.py` - Skill discovery, YAML frontmatter parsing, XML-style prompt generation
  - `tokens.py` - Token estimation via tiktoken with character fallback
  - `tools/` - Tool registry and built-in tools
    - `registry.py` - Central tool registry with auto-discovery
    - `terminal.py` - Shell command execution with timeout and output truncation
    - `file_ops.py` - read_file, write_file, patch_file tools
    - `search_files.py` - Grep/regex search across project files
    - `web.py` - DuckDuckGo HTML web search (zero dependencies)
    - `skills_tool.py` - skills_list, skill_view, skill_manage tools
    - `memory_tool.py` - memory tool (add/search/delete/clear)

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
