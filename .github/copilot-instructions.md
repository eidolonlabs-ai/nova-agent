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
- Test: `pytest`
- Run: `nova chat` or `nova ask "question"`

## Configuration
Copy `config.yaml.example` to `config.yaml` and set your OpenRouter API key.

## Project Status
- All 18 tests passing
- Linting clean (ruff)
- CLI functional (chat, ask, sessions, reset)
- Ready for configuration and first run
