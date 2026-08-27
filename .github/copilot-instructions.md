# Nova Agent - Copilot Instructions

> **Repository:** https://github.com/eidolonlabs-ai/nova-agent
> **Organization:** Eidolon Labs LLC

## Project Overview
Nova Agent is a lightweight personal AI agent with explicit token budgets and smart context management.

## Architecture
- **nova/** - Main package
  - `agent.py` - Main agent loop with OpenAI-compatible API, streaming, tool calling, compaction
  - `cli.py` - CLI entry point (chat, ask, sessions, reset commands)
  - `config.py` - YAML config loading with env var resolution, deep merge, validation
  - `context.py` - Context file discovery with budgets, head/tail truncation, injection scanning
  - `wiki_memory.py` - Obsidian-compatible wiki memory (markdown notes, `[[wikilinks]]`, `Core/` auto-inject)
  - `model_metadata.py` - Model context window and pricing metadata from the provider's models endpoint
  - `prompt.py` - System prompt assembly with mode gating (full/minimal/none)
  - `session.py` - SQLite session storage with FTS5 full-text search
  - `skills.py` - Skill discovery, YAML frontmatter parsing, XML-style prompt generation
  - `tokens.py` - Token estimation via tiktoken with character fallback
  - `mcp_client.py` - MCP client (stdio, HTTP, SSE transports) with hardened stdio handling
  - `tasks.py` - Background task manager (fire-and-forget shell execution)
  - `tools/` - Tool registry and built-in tools
    - `registry.py` - Central tool registry with auto-discovery, read-only classification
    - `terminal.py` - Shell command execution with timeout and output truncation
    - `file_ops.py` - read_file, write_file, patch_file tools
    - `path_safety.py` - Shared workspace/sensitive-path validation for file tools
    - `search_files.py` - Grep/regex search across project files
    - `web.py` - Firecrawl web tools (search, scrape, map, crawl, extract, parse, dev search, usage)
    - `firecrawl_client.py` - Firecrawl SDK client, error translation, document formatting
    - `http_client.py` - SSRF-hardened HTTP tools (get/post/put/delete)
    - `git_tool.py` - git_status/diff/log/show/blame tools
    - `skills_tool.py` - skills_list, skill_view, skill_manage, skill_export tools
    - `wiki_tool.py` - wiki tool (write/append/read/search/list/delete/maintenance)
    - `task_tools.py` - task_create/status/output/stop/list tools

## Key Design Principles
1. **Explicit token budgets** at every layer (system prompt, skills, context files, tool results)
2. **Two-tier tool descriptions** - compact list in prompt + JSON schemas to API
3. **Head/tail truncation** (70/20 ratio) for context files
4. **Prompt mode gating** - full/minimal/none for different agent types
5. **Prompt injection scanning** for security
6. **Untrusted external content** (web, HTTP, MCP) is truncated and labeled as data, not instructions

## Development Commands
- Lint: `ruff check .`
- Auto-fix: `ruff check --fix .`
- Format: `ruff format .`
- Type check: `mypy nova/`
- Test: `pytest`
- Full CI check: `ruff check . && ruff format --check . && mypy nova/ && pytest`
- Run: `nova chat` or `nova ask "question"`

## Code Quality Standards
- **Type hints**: All public functions should have type annotations. Run `mypy nova/` to verify.
- **Linting**: Code must pass `ruff check .` with no errors.
- **Tests**: All tests must pass. New features should include tests that verify real behavior (prefer asserting values over `is not None`).
- **Test structure**: Tests use dependency injection — pass mock `openai_client`, `session_store`, and `wiki_memory_store` to `NovaAgent` for isolated testing.
- **Test files**: `tests/test_agent.py`, `tests/test_config.py`, `tests/test_context.py`, `tests/test_cli.py`, `tests/test_wiki_memory.py`, `tests/test_model_metadata.py`, `tests/test_prompt.py`, `tests/test_session.py`, `tests/test_skills.py`, `tests/test_tokens.py`, `tests/test_web_tools.py`, `tests/test_mcp_client.py`, `tests/test_tasks.py`

## Configuration
Copy `config.yaml.example` to `config.yaml` and set your `LLM_API_KEY` (or legacy `OPENROUTER_API_KEY`).

## Project Status
- Full test suite passing (`pytest` for current count; coverage ≥ 70%)
- Linting clean (ruff)
- Type checking clean (mypy, 0 errors)
- CLI functional (chat, ask, sessions, reset)
- 35+ tools available (terminal, file ops, search, git, http, web/Firecrawl, skills, wiki, tasks, session search, MCP resources)
