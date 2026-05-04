# Nova Agent — Documentation Index

**Last Updated:** May 2026  
**Status:** ✅ Active  
**Maintainer:** [Eidolon Labs LLC](https://github.com/eidolonlabs-ai)

> Systematic inventory of all Nova Agent documentation.

---

## 🎯 Start Here

| Document | Purpose |
|----------|---------|
| **[README](../README.md)** | Project overview, features, quick start, installation |
| **[GUIDE-003-CUSTOMIZING](GUIDE-003-CUSTOMIZING.md)** | Config, SOUL.md, models, budgets, skills, memory — the full guide |
| **[CONTRIBUTING](../CONTRIBUTING.md)** | Development setup, code standards, PR workflow |

---

## 📚 Guides (GUIDE-NNN)

| Document | Status | What It Covers |
|----------|--------|----------------|
| [GUIDE-001-CREATING_TOOLS](GUIDE-001-CREATING_TOOLS.md) | ✅ Active | Build custom tools: schema, handler, registration, tests |
| [GUIDE-002-CREATING_SKILLS](GUIDE-002-CREATING_SKILLS.md) | ✅ Active | Write SKILL.md files for specialized knowledge domains |
| [GUIDE-003-CUSTOMIZING](GUIDE-003-CUSTOMIZING.md) | ✅ Active | Config, SOUL.md, models, token budgets, tools, sessions |
| [GUIDE-004-BACKGROUND_TASKS](GUIDE-004-BACKGROUND_TASKS.md) | ✅ Active | Fire-and-forget shell execution with status tracking |
| [GUIDE-005-COST_TRACKING](GUIDE-005-COST_TRACKING.md) | ✅ Active | Token usage, dollar cost estimation, per-model pricing |
| [GUIDE-006-HOOKS](GUIDE-006-HOOKS.md) | ✅ Active | Lifecycle callbacks: pre/post tool call, LLM call, session |
| [GUIDE-007-MCP_INTEGRATION](GUIDE-007-MCP_INTEGRATION.md) | ✅ Active | Connect stdio, HTTP, and SSE Model Context Protocol servers |
| [GUIDE-008-PERMISSIONS](GUIDE-008-PERMISSIONS.md) | ✅ Active | Defense-in-depth cascade, allow/deny lists, path rules |

---

## 🏗️ Architecture Decision Records (ADR-NNN)

| Document | Status | What It Covers |
|----------|--------|----------------|
| [ADR-001-SUBAGENT_COMPARISON](ADR-001-SUBAGENT_COMPARISON.md) | ✅ Active | Sub-agent architecture comparison and tradeoffs |
| [ADR-002-SUBAGENT_DESIGN](ADR-002-SUBAGENT_DESIGN.md) | ✅ Active | Sub-agent design decisions and implementation approach |
| [ADR-003-TOOL_SYSTEM_REVIEW](ADR-003-TOOL_SYSTEM_REVIEW.md) | ✅ Active | Tool system design review and architectural notes |

---

## 📋 Reports (REPORT-NNN)

| Document | Status | What It Covers |
|----------|--------|----------------|
| [REPORT-001-PROJECT_STATUS_2026-05-02](REPORT-001-PROJECT_STATUS_2026-05-02.md) | ✅ Active | Test coverage baseline, CI status, open work as of May 2026 |

---

## 🧩 Starter Skills

Skills live in `config/skills/` — copy to `~/.nova/skills/` to activate.

| Skill | Category | Status | What It Covers |
|-------|----------|--------|----------------|
| `python-coding` | development | ✅ Active | Type hints, PEP 8, pytest, ruff, mypy, venvs |
| `git-workflow` | development | ✅ Active | Branching, committing, pushing, PRs |
| `file-editing` | development | ✅ Active | Safe file editing patterns, verification steps |
| `code-review` | development | ✅ Active | Code review conventions and checklists |
| `documentation-template-builder` | development | ✅ Active | Generate docs in ai-companions style (README, Roadmap, Spec, ADR, etc.) |
| `nova-development` | development | ✅ Active | Tool system, permissions, hooks, testing patterns, config, architecture, and CI |

---

## 📊 Documentation Status Summary

| Category | Count | Status |
|----------|-------|--------|
| Guides (GUIDE-NNN) | 8 | ✅ All current |
| ADRs (ADR-NNN) | 3 | ✅ All current |
| Reports (REPORT-NNN) | 1 | ✅ Current |
| Starter skills | 6 | ✅ All current |
| Root docs (README, CONTRIBUTING, SECURITY) | 3 | ✅ All current |
| **Total** | **21** | ✅ |

---

## 🆘 Troubleshooting

1. **Can't connect to OpenRouter** → Check `OPENROUTER_API_KEY` env var or `config.yaml`
2. **Tool blocked unexpectedly** → See [GUIDE-008-PERMISSIONS](GUIDE-008-PERMISSIONS.md) — check `denied_tools` and `path_rules`
3. **Context too long / compression triggering** → See [GUIDE-003-CUSTOMIZING](GUIDE-003-CUSTOMIZING.md#context-compression) — adjust `threshold_percent`
4. **MCP server not appearing** → See [GUIDE-007-MCP_INTEGRATION](GUIDE-007-MCP_INTEGRATION.md#troubleshooting)
5. **Skills not loading** → Check `~/.nova/skills/<name>/SKILL.md` exists with valid YAML frontmatter
