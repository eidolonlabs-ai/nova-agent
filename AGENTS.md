# Nova Agent — Codex Instructions

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
- `wiki_memory.py` — Obsidian-compatible wiki memory (markdown notes, `[[wikilinks]]`, `Core/` auto-inject, maintenance reporting)
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
  - `wiki_tool.py` — wiki tool (write/append/read/search/list/delete/maintenance)

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
ruff format .             # Format code
ruff format --check .     # Check formatting (CI)

# Type checking
mypy nova/

# Testing
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest --cov=nova         # Coverage report

# Security scan
pip-audit                 # Check for CVEs in dependencies

# Full CI check
ruff check . && ruff format --check . && mypy nova/ && pytest
```

### Running the Agent

```bash
nova chat                 # Interactive chat
nova ask "question"       # Single question
nova sessions             # List sessions
nova reset                # Reset session state
```

## Code Quality Standards

**Type hints:** All public functions require type annotations. Verify with `mypy nova/` (0 errors in 36 source files).

**Linting:** Code must pass `ruff check .` with no errors.

**Tests:** All 768 tests must pass.
- Test coverage baseline: CLI 82%, sessions/file_ops 91–100%
- Use dependency injection: pass mock `http_client`, `session_store`, and `wiki_memory_store` to `NovaAgent`
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
2. Set your API key: `LLM_API_KEY=...` (or `OPENROUTER_API_KEY` for legacy)
3. Optionally customize model, max_tokens, temperature, system_prompt_mode

## Testing Notes

- Tests use `pytest` with fixtures in `conftest.py`
- Mock HTTP client, session store, and wiki memory store for isolation
- Full CI check: `ruff check . && ruff format --check . && mypy nova/ && pytest`
- Coverage minimum: 70% (enforced by CI); target 80%+ for new code

## Current Status

✅ All 768 tests passing
✅ Linting clean (ruff)
✅ Type checking clean (mypy)
✅ Coverage: 75.69% (exceeds 70% minimum)
✅ CLI functional (chat, ask, sessions, reset)
✅ 10+ tools available (terminal, read_file, write_file, patch_file, search_files, web_search, skills_list, skill_view, skill_manage, wiki, git, http_client, etc.)

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

**Adding skills:** See [docs/GUIDE-002-CREATING_SKILLS.md](docs/GUIDE-002-CREATING_SKILLS.md) for skill format and examples.

**Full contribution guidelines:** See [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentation Standards

> **Before writing any doc, load the skill:** `skill_view("documentation-template-builder")` — it has templates and rich examples for every doc type.

All documentation for this project follows **ai-companions style**. These rules apply whenever you create or edit any `.md` file in this repo.

**File placement:** Every doc lives in `docs/`. Never create `.md` files at the repo root (except README.md, CONTRIBUTING.md, SECURITY.md, AGENTS.md).

**Naming convention — always use the correct type prefix:**

| Type | Prefix | When to use |
|------|--------|-------------|
| Feature/usage guide | `GUIDE-NNN-NAME.md` | How-to docs, developer references |
| Product requirements | `PRD-NNN-NAME.md` | Feature requirements, user stories, acceptance criteria |
| User personas | `PERSONA-NNN-NAME.md` | Who we're building for — goals, frustrations, behaviors |
| Architecture decision | `ADR-NNN-NAME.md` | Design decisions and rationale |
| Technical specification | `SPEC-NNN-NAME.md` | Feature design, data models, APIs |
| Deployment/runbook | `RUN-NNN-NAME.md` | Step-by-step operational procedures |
| Release notes | `RELEASE-NNN-NAME.md` | Customer-facing changelog for a version |
| Product strategy | `STRATEGY-NNN-NAME.md` | Vision, bets, OKRs, long-term direction |
| Competitive analysis | `RESEARCH-NNN-NAME.md` | Market landscape, competitor teardowns, positioning |
| Go-to-market plan | `GTM-NNN-NAME.md` | Launch coordination across PM, Marketing, CS |
| Status/project report | `REPORT-NNN-NAME.md` | Point-in-time project status |

Use the next available number in sequence. Check `docs/DOCUMENTATION_INDEX.md` for the current highest number per type.

**Required metadata in every doc** (first 5 lines after the title):
```markdown
**Status:** ✅ Active
**Last Updated:** Month YYYY
**Type:** GUIDE (Developer Reference)   ← match the prefix type
```

**Status indicators** — use consistently:
- `✅` Active / complete / passing
- `🟡` In progress / partial
- `📋` Planned / not started
- `🔴` Blocked / deprecated

**Every doc must include:**
- A Related Documentation section at the bottom with a cross-reference table
- Status symbols in any feature or capability tables

## Working in Worktrees

When you create or enter a worktree, make sure to:
1. Set up the venv: `python3 -m venv .venv`
2. Install: `.venv/bin/pip install -e ".[dev]"`
3. Run tests to ensure isolation: `.venv/bin/pytest`

Use `.venv/bin/python`, `.venv/bin/pytest`, and `.venv/bin/ruff` — never global python3 or pytest.
