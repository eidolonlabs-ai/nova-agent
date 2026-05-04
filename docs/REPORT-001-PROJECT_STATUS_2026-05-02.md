# Nova Agent — Project Report

**Date:** 2026-05-02

---

## Overview

| Metric | Value |
|--------|-------|
| **Version** | 0.1.0 |
| **Language** | Python 3.12+ |
| **License** | MIT |
| **Repository** | https://github.com/eidolonlabs-ai/nova-agent |
| **Build** | setuptools (editable install) |
| **API** | OpenRouter (100+ models) |

---

## Code Statistics

### Source Code

| Category | Files | Lines |
|----------|-------|-------|
| Core modules | 18 | 6,975 |
| Tools | 10 | 1,765 |
| **Total source** | **28** | **8,740** |

### Tests

| Category | Files | Tests |
|----------|-------|-------|
| Core tests | 13 | 101 |
| New feature tests | 6 | 175 |
| **Total tests** | **19** | **276** |

### Documentation

| File | Purpose |
|------|---------|
| `README.md` | Project overview, features, installation |
| `docs/GUIDE-003-CUSTOMIZING.md` | Full customization guide |
| `docs/GUIDE-001-CREATING_TOOLS.md` | Custom tool development |
| `docs/GUIDE-002-CREATING_SKILLS.md` | Custom skill development |
| `docs/GUIDE-008-PERMISSIONS.md` | Permission system |
| `docs/GUIDE-006-HOOKS.md` | Hook/callback system |
| `docs/GUIDE-004-BACKGROUND_TASKS.md` | Background task management |
| `docs/GUIDE-007-MCP_INTEGRATION.md` | MCP server integration |
| `docs/GUIDE-005-COST_TRACKING.md` | Cost tracking and usage |

---

## Top 10 Largest Files

| File | Lines |
|------|-------|
| `nova/agent.py` | 780 |
| `nova/display.py` | 759 |
| `nova/mcp_client.py` | 703 |
| `nova/cli.py` | 247 |
| `nova/session.py` | 236 |
| `nova/permissions.py` | 233 |
| `nova/tools/task_tools.py` | 233 |
| `nova/tools/delegate_tool.py` | 323 |
| `nova/tools/file_ops.py` | 287 |
| `nova/tasks.py` | 338 |

---

## New Modules (Session Additions)

| Module | Lines | Purpose |
|--------|-------|---------|
| `nova/permissions.py` | 233 | Permission system with defense-in-depth |
| `nova/mcp_client.py` | 703 | MCP client (stdio, HTTP, SSE) |
| `nova/tasks.py` | 338 | Background task manager |
| `nova/tools/task_tools.py` | 233 | Task management tools (5 tools) |
| `nova/hooks.py` | 100 | Hook/callback system |
| `nova/cost_tracker.py` | 150 | Dollar cost tracking |
| `nova/microcompact.py` | 100 | Cheap context compaction |
| `nova/compression.py` | 201 | LLM-based context compression |
| `nova/retry.py` | 203 | Retry with exponential backoff |
| **New total** | **~2,261** | |

New modules account for ~26% of total codebase.

---

## CI Status

| Check | Status |
|-------|--------|
| Ruff (lint) | ✅ Pass |
| Mypy (type check) | ✅ 0 errors in 32 files |
| Pytest (tests) | ✅ 302 passed |

---

## Built-in Tools (16)

| Tool | Toolset | Description |
|------|---------|-------------|
| `terminal` | terminal | Shell command execution |
| `read_file` | file | Read files with line ranges |
| `write_file` | file | Write files with atomic saves |
| `patch_file` | file | Search/replace patches |
| `search_files` | file | Grep/regex search |
| `web_search` | web | Bing RSS web search |
| `skills_list` | skills | List skills by category |
| `skill_view` | skills | Load skill instructions |
| `skill_manage` | skills | Create/update/delete skills |
| `memory` | memory | Persistent memory CRUD |
| `delegate_task` | delegation | Spawn sub-agents |
| `task_create` | tasks | Start background task |
| `task_status` | tasks | Check task status |
| `task_output` | tasks | Read task output |
| `task_stop` | tasks | Stop background task |
| `task_list` | tasks | List all tasks |

---

## Configuration Sections

| Section | Purpose |
|---------|---------|
| `openrouter` | API key, model, base URL |
| `agent` | Identity, max iterations, temperature |
| `budgets` | Token budgets at every layer |
| `compression` | LLM-based context compression |
| `context_files` | Auto-discovered context files |
| `memory` | Persistent memory settings |
| `skills` | Skills directory and limits |
| `session` | SQLite session storage |
| `logging` | Log level and file |
| `delegation` | Sub-agent spawning config |
| `permissions` | Tool execution approval |
| `mcp` | MCP server connections |
| `cost_tracking` | Usage and cost tracking |
| `microcompact` | Tier 1 context compaction |
| `retry` | API retry with backoff |

---

## Design Principles

1. **Explicit token budgets** at every layer
2. **Two-tier tool descriptions** — compact prompt + JSON schema
3. **Head/tail truncation** (70/20 ratio) for context files
4. **Prompt mode gating** — full/minimal/none
5. **Dependency injection** for testability
6. **Config layering** — defaults → global → local

---

## Key Design Patterns

- **Tool registry** — auto-discovery via `registry.register()` at import time
- **SQLite + FTS5** — session storage with full-text search
- **JSON file memory** — LRU eviction, atomic writes
- **Skill discovery** — YAML frontmatter, XML-style index
- **Permission cascade** — sensitive paths → tool deny/allow → path rules → command deny → mode
- **Hook system** — pre/post tool/llm call, session lifecycle
- **Two-tier compaction** — microcompact (cheap) → LLM summarization (Tier 2)
- **Retry with backoff** — exponential backoff, jitter, error classification

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12+ |
| HTTP Client | httpx |
| Token Estimation | tiktoken (cl100k_base) |
| Terminal UI | prompt_toolkit + rich |
| Config | pyyaml |
| Session Storage | SQLite + FTS5 |
| Memory | JSON file |
| Build | setuptools |
| Linting | ruff |
| Type Checking | mypy |
| Testing | pytest |
| API | OpenRouter |

---

## Config Examples

| File | Purpose |
|------|---------|
| `config.yaml.example` | Full config with all options |
| `config-minimal.yaml.example` | Bare minimum (API key + model) |
| `config-full.yaml.example` | Every option with explanations |
| `config-safe.yaml.example` | Permissions locked down |

---

*Report generated: 2026-05-02*
