# Nova Agent — Project Roadmap

**Updated:** August 2026
**Current Phase:** Release hardening
**Overall Progress:** ACP integration complete; release hardening in progress

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
- ✅ MCP integration (stdio, HTTP, SSE servers; agent-local namespaced tools)
- ✅ Sub-agent delegation (worker thread with own budget and timeout)
- ✅ Automatic retry (exponential backoff + jitter)
- ✅ Prompt mode gating (full for main agent, minimal for sub-agents)
- ✅ Firecrawl web tools via the official Python SDK (search, scrape, map, crawl, extract, parse)
- ✅ Obsidian-compatible wiki memory (markdown notes, `[[wikilinks]]`, `Core/` auto-inject, maintenance)
- ✅ ACP stdio server (session lifecycle, workspace isolation, tool-call progress)

## Phase 3: Reliability & Scale 🟡 In Progress (Jun–Aug 2026)

Making Nova production-ready for teams and long sessions.

- 🟡 **Context window optimization** — adaptive compression based on session length
- 🟡 **Multi-model fallback** — if one model fails, try another automatically
- 📋 **Session archival** — move old persisted sessions to cold storage
- 📋 **Structured output mode** — force JSON responses for tool-heavy workflows
- 📋 **Plugin system** — third-party tool/skill marketplace
- ✅ **Parallel tool execution** — run independent read-only tools concurrently
- ✅ **Harness observability** — optional Langfuse telemetry, secret-safe traces, and file postcondition verification

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
| Phase 3 | Aug 2026 | 🟡 In progress | Context optimization, multi-model fallback, release hardening |
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

1. **Release hardening** — validate security boundaries, supported Python versions, and installation paths
2. **Context window optimization** — adaptive compression unblocks long-session reliability
3. **Multi-model fallback** — reduces outage risk from OpenRouter downtime

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Documentation Index](DOCUMENTATION_INDEX.md) | Full inventory of all docs |
| [REPORT-002 ACP Handoff](REPORT-002-ACP_IMPLEMENTATION_HANDOFF.md) | ACP implementation and verification |
| [ADR-001 Sub-Agent Comparison](ADR-001-SUBAGENT_COMPARISON.md) | Architecture decision for delegation |
| [ADR-002 Sub-Agent Design](ADR-002-SUBAGENT_DESIGN.md) | Implementation approach |
| [CONTRIBUTING](../CONTRIBUTING.md) | How to contribute to Nova |
