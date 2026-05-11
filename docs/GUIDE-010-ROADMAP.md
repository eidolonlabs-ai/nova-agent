# Nova Agent — Project Roadmap

**Updated:** May 2026  
**Current Phase:** Phase 3 — Reliability & Scale  
**Overall Progress:** 70% complete (14/20 features)

---

## Phase 1: Core Agent ✅ Completed (Jan–Mar 2026)

The foundation: tool registry, context management, and the chat interface.

- ✅ Tool registry with JSON schema definitions
- ✅ Explicit token budgets at every layer (system, skills, context, history)
- ✅ Smart context management (head/tail truncation, LLM compression)
- ✅ Session storage with SQLite + FTS5 full-text search
- ✅ Core tool set (terminal, file ops, search, HTTP, git)
- ✅ Skills system with SKILL.md discovery
- ✅ OpenRouter API integration (100+ models)
- ✅ Streaming terminal UI

## Phase 2: Safety & Extensibility ✅ Completed (Apr–May 2026)

Made Nova safe to run and extensible for real-world use.

- ✅ Permission system (defense-in-depth cascade, allow/deny lists, path rules)
- ✅ Hook/callback system (pre/post tool call, LLM call, session lifecycle)
- ✅ Cost tracking (per-model pricing, dollar estimation)
- ✅ Background task system (fire-and-forget shell execution)
- ✅ MCP integration (stdio, HTTP, SSE servers)
- ✅ Sub-agent delegation (worker thread with own budget and timeout)
- ✅ Automatic retry (exponential backoff + jitter)
- ✅ Prompt mode gating (full for main agent, minimal for sub-agents)
- ✅ Web search via Bing RSS (zero dependencies, zero API key)
- ✅ Obsidian-compatible wiki memory (markdown notes, `[[wikilinks]]`, `Core/` auto-inject, maintenance)

## Phase 3: Reliability & Scale 🟡 In Progress (Jun–Aug 2026)

Making Nova production-ready for teams and long sessions.

- 🟡 **Context window optimization** — adaptive compression based on session length
- 🟡 **Multi-model fallback** — if one model fails, try another automatically
- 📋 **Session archival** — move old sessions to cold storage
- 📋 **Structured output mode** — force JSON responses for tool-heavy workflows
- 📋 **Plugin system** — third-party tool/skill marketplace
- 📋 **Parallel tool execution** — run independent tools simultaneously

## Phase 4: Team Features 📋 Planned (Sep–Dec 2026)

Collaboration and enterprise readiness.

- 📋 **Shared session history** — team can browse and resume sessions
- 📋 **Role-based permissions** — admin, developer, read-only
- 📋 **Audit logging** — track all tool calls and responses
- 📋 **Custom skill templates** — generate skills from natural language
- 📋 **CLI completions** — tab-completion for slash commands

---

## Timeline

| Phase | Target | Status | Key Deliverables |
|-------|--------|--------|-----------------|
| Phase 1 | Mar 2026 | ✅ Complete | Core agent, tools, skills |
| Phase 2 | May 2026 | ✅ Complete | Permissions, hooks, MCP, delegation |
| Phase 3 | Aug 2026 | 🟡 50% | Context optimization, multi-model fallback |
| Phase 4 | Dec 2026 | 📋 Planned | Shared sessions, RBAC, audit logs |

---

## Notable Omissions

The following are explicitly **not** on the roadmap (trade-offs, not oversights):

- ❌ **GUI application** — terminal-first by design; web UI would add maintenance overhead
- ❌ **Local LLM support** — OpenRouter is the focus; local models can work via custom API endpoint
- ❌ **Mobile app** — Nova is a developer tool for desktop use
- ❌ **Multi-language support** — English-first; i18n would be a Phase 4+ effort

---

## Next Steps

1. **Context window optimization** — adaptive compression unblocks long-session reliability
2. **Multi-model fallback** — reduces outage risk from OpenRouter downtime
3. **Plugin system design** — community contributions will accelerate Phase 4

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Documentation Index](docs/DOCUMENTATION_INDEX.md) | Full inventory of all docs |
| [REPORT-001 Project Status](docs/REPORT-001-PROJECT_STATUS_2026-05-02.md) | Latest project snapshot |
| [ADR-001 Sub-Agent Comparison](docs/ADR-001-SUBAGENT_COMPARISON.md) | Architecture decision for delegation |
| [ADR-002 Sub-Agent Design](docs/ADR-002-SUBAGENT_DESIGN.md) | Implementation approach |
| [CONTRIBUTING](CONTRIBUTING.md) | How to contribute to Nova |
