# Rich Example: Roadmap Documentation

> Illustrative roadmap in ai-companions style. Adjust phases, dates, and spec IDs for your project.

---

# AI Companions Documentation Roadmap

**Updated:** May 3, 2026  
**Current Phase:** Phase 2 (Narrative Depth & User Experience)  
**Overall Status:** 29/35 specs complete (83%)

---

## Phase 1: Stability & Advanced Reasoning ✅ Completed (Jan–Apr 2026)

### Agentic Improvements
- ✅ [SPEC-015](docs/spec/SPEC-015-AGENTIC_WORKFLOW.md) — Unified agentic architecture
- ✅ Response guidelines optimization for recency bias
- ✅ Token-based history compression (budget history)

### Infrastructure Refactor
- ✅ [SPEC-016](docs/spec/SPEC-016-PG_KNOWLEDGE_GRAPH.md) — PostgreSQL knowledge graph
- ✅ Arc Memory superseded fact tracking
- ✅ [SPEC-017](docs/spec/SPEC-017-LLM_ROBUSTNESS.md) — JSON extraction & retry logic

### Cross-Platform Alignment
- ✅ Firestore real-time sync
- ✅ Unified streaming (Web, Android, iOS)

---

## Phase 2: Narrative Depth & User Experience 🟡 In Progress (May–Aug 2026)

### P1: Narrative Continuity
- ✅ [SPEC-018](docs/spec/SPEC-018-REFLECTIVE_AGENT_IMPROVEMENTS.md) — Socially aware agent
- 🟡 SPEC-019: Long-term goal evolution (50% complete)
- 🔴 SPEC-020: Personality drift (blocked by SPEC-019)
- 📋 [SPEC-073](docs/spec/SPEC-073-SHARED_LORE_ARCHITECTURE.md) — Shared lore & world building
- 📋 ADR-040: Context window optimization

### P2: User Retention & Social
- 🟡 SPEC-046: Community templates (in review)
- 🟡 SPEC-047: Group chat (design phase)
- 📋 SPEC-048: Advanced insights (queued)

---

## Phase 3: Scale & Monetization 📋 Planned (Sep–Dec 2026)

- 📋 Multi-user support
- 📋 Premium features
- 📋 Third-party integrations
- 📋 Enterprise deployment

---

## Summary

| Phase | Features | Status | ETA |
|-------|----------|--------|-----|
| Phase 1 | 12 specs | ✅ Complete | Jan 2026 |
| Phase 2 | 13 specs | 🟡 70% | Aug 2026 |
| Phase 3 | 10 specs | 📋 Planned | Dec 2026 |

## Blocked Items

| Item | Reason | Unblocks | ETA |
|------|--------|----------|-----|
| SPEC-020 | Waiting on SPEC-019 | Personality drift | Jun 15 |
| ADR-040 | Design review pending | Context optimization | Jun 30 |

## Recommended Next Steps

1. **Complete SPEC-019** (Long-term goal evolution) — unblocks personality drift
2. **Finalize group chat design** (SPEC-047) — dependency for community templates
3. **Polish Android UI** — Material 3 updates to Memory Manager

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Documentation Index](docs/DOCUMENTATION_INDEX.md) | Full inventory of all specs |
| [Project Status Report](docs/REPORT-001-PROJECT_STATUS.md) | Latest status snapshot |
