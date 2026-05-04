---
name: documentation-template-builder
category: development
description: Generate project documentation in ai-companions style — README, roadmap, GUIDE, SPEC (specification), ADR (architecture decision record), RUN doc (runbook, deployment guide), operational guide, REPORT (status report). Use when creating, writing, or updating any project docs. Produces complete markdown with status indicators (✅🟡📋), quick reference tables, and Related Documentation sections. In nova-agent projects, files live in docs/ with prefixes GUIDE-NNN, SPEC-NNN, ADR-NNN, RUN-NNN, REPORT-NNN.
---

# Documentation Template Builder

Generate professional project documentation in ai-companions style: status symbols, quick reference tables, cross-referenced structure, and complete content (not just empty scaffolding).

**Rich examples available.** Load any of these via `read_file` when you need a detailed reference:
- `~/.nova/skills/documentation-template-builder/references/readme-example.md`
- `~/.nova/skills/documentation-template-builder/references/roadmap-example.md`
- `~/.nova/skills/documentation-template-builder/references/spec-example.md`
- `~/.nova/skills/documentation-template-builder/references/deployment-example.md`
- `~/.nova/skills/documentation-template-builder/references/adr-example.md`
- `~/.nova/skills/documentation-template-builder/references/operational-example.md`

---

## Nova-Agent File Naming Conventions

All docs live in `docs/`. Use the correct type prefix and sequence number:

| Type | Pattern | When to use |
|------|---------|-------------|
| Feature/usage guide | `GUIDE-NNN-NAME.md` | How-to docs, developer references |
| Specification | `SPEC-NNN-NAME.md` | Feature design, data models, APIs |
| Architecture decision | `ADR-NNN-NAME.md` | Design decisions and rationale |
| Deployment/runbook | `RUN-NNN-NAME.md` | Step-by-step operational procedures |
| Status/project report | `REPORT-NNN-NAME.md` | Point-in-time project status |

**Getting the number:** Check `docs/DOCUMENTATION_INDEX.md` for the highest number in use per type. Use the next in sequence.

**NAME format:** All-caps with underscores. Example: `GUIDE-009-SESSION_MANAGEMENT.md`

**Exceptions:** `README.md` (repo root), `CONTRIBUTING.md`, `SECURITY.md`, `CLAUDE.md` stay at the root without prefixes.

---

## Core Documentation Principles

### Structure & Hierarchy
- Header hierarchy: `# Title` → `## Section` → `### Subsection`
- Start every doc with metadata in the first 3–5 lines after the title: **Status**, **Last Updated**, **Type**
- Include a "Quick Reference" or "Quick Start" section near the top
- Group related content in tables for scannability

### Status Symbols
Use consistently throughout all docs:
- `✅` — Complete, active, production-ready
- `🔴` — Blocked, critical issue, deprecated
- `🟡` — In progress, partial, needs review
- `📋` — Planned, roadmap item, pending
- `✏️` — Draft, being written
- `⚠️` — Warning, deprecated but still used
- `🔗` — Reference link, related doc

### Cross-referencing
- Every doc must end with a `## Related Documentation` table
- Use descriptive link text: `[SPEC-015 Agentic Workflow](path)` not `[here](path)`
- Format: `| [DOC-NNN Title](path) | One-line description |`

---

## 1. README (Project Overview)

**Purpose:** First thing people read. Balance welcoming with informative.  
**File:** `README.md` at repo root.

**Required sections:** Tagline, Status at a glance, Quick start, Features table, Documentation index, Contributing, License.

```markdown
# Project Name

**Status:** ✅ Active in production  
**Latest Release:** v2.1.0 (May 2026)  
**By:** [Author/Org](https://github.com/org)

> One-sentence description of what this project does and who it's for.

## Quick Start

```bash
git clone <url>
cd <dir>
make install
make dev
```

## Features

| Feature | Status | Details |
|---------|--------|---------|
| Feature one | ✅ Active | What it does and why it matters |
| Feature two | ✅ Active | What it does and why it matters |
| Coming soon | 📋 Planned | Brief description |

## Documentation

| Document | Type | Purpose |
|----------|------|---------|
| [Setup Guide](docs/GUIDE-NNN-SETUP.md) | GUIDE | Installation and configuration |
| [Architecture](docs/ADR-NNN-ARCHITECTURE.md) | ADR | Design decisions |
| [Contributing](CONTRIBUTING.md) | — | How to contribute |

## License

MIT — see [LICENSE](LICENSE) for details.
```

**Rich example:** Load `references/readme-example.md` for a full nova-agent-based README.

---

## 2. Roadmap (Phases & Timeline)

**Purpose:** Show project direction, completed work, and what's next.  
**File:** `docs/GUIDE-NNN-ROADMAP.md` (or `ROADMAP.md` at root for high-visibility projects).

**Required sections:** Current phase + overall progress, Phase breakdowns with status symbols, Timeline table, Blocked items, Next steps.

```markdown
# Project Roadmap

**Updated:** May 2026  
**Current Phase:** Phase 2 — User Experience  
**Overall Progress:** 65% complete (13/20 features)

---

## Phase 1: Core Features ✅ Completed

- ✅ Feature A — shipped Jan 2026
- ✅ Feature B — shipped Feb 2026

## Phase 2: User Experience 🟡 In Progress

- ✅ Subfeature 1 — complete
- 🟡 Subfeature 2 — 50% done
- 📋 Subfeature 3 — queued

## Phase 3: Scaling 📋 Planned

- 📋 Performance optimization
- 📋 Multi-region deployment

---

## Timeline

| Phase | Target | Status |
|-------|--------|--------|
| Phase 1 | Jan 2026 | ✅ Complete |
| Phase 2 | Jun 2026 | 🟡 70% |
| Phase 3 | Dec 2026 | 📋 Planned |

## Next Steps

1. **Complete Subfeature 2** — unblocks Subfeature 3
2. **Begin Phase 3 design** — target kickoff Jul 1

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Documentation Index](docs/DOCUMENTATION_INDEX.md) | Full inventory of all specs |
| [Status Report](docs/REPORT-NNN-STATUS.md) | Latest project snapshot |
```

**Rich example:** Load `references/roadmap-example.md` for a multi-phase roadmap with blocked items.

---

## 3. Specification (SPEC)

**Purpose:** Detailed design of a single feature, system, or component.  
**File:** `docs/SPEC-NNN-FEATURE_NAME.md`

**Required sections:** Problem statement, Proposed solution, Architecture, Data model (if applicable), API/Interface, Examples, Trade-offs, Related documentation.

```markdown
# SPEC-NNN: Feature Name

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** SPEC (Feature Specification)  
**Author:** Name

---

## Problem

What problem does this feature solve? 2–3 sentences max.

## Solution

High-level approach: what we're building and how.

## Architecture

```
[ASCII diagram or prose description of components]
```

## Data Model

```sql
CREATE TABLE feature_name (
  id UUID PRIMARY KEY,
  created_at TIMESTAMP NOT NULL,
  status TEXT NOT NULL
);
```

## API

```python
def create_feature(name: str, config: dict) -> Feature:
    ...
```

## Examples

### Basic usage
```python
result = create_feature("example", {"enabled": True})
```

## Trade-offs

| Decision | Alternative | Rationale |
|----------|-------------|-----------|
| Choice A | Choice B | Why A wins here |

## Related Documentation

| Document | Purpose |
|----------|---------|
| [SPEC-NNN](SPEC-NNN.md) | Dependent feature |
| [ADR-NNN](ADR-NNN.md) | Architecture decision this spec follows |
```

**Rich example:** Load `references/spec-example.md` for a complete socially-aware agent spec.

---

## 4. Deployment Guide / Runbook (RUN)

**Purpose:** Step-by-step instructions for deploying or operating the system.  
**File:** `docs/RUN-NNN-DEPLOY_TO_ENV.md`

**Required sections:** Prerequisites checklist, Quick steps (for experienced users), Detailed walkthrough, Verification, Rollback, Troubleshooting.

```markdown
# RUN-NNN: Deploy to [Environment]

**Last Updated:** May 2026  
**Type:** RUN (Operational Procedure)  
**Audience:** DevOps, Release Manager

---

## Prerequisites

- [ ] All tests passing (`pytest` or equivalent)
- [ ] Config file ready (`config.yaml`)
- [ ] Database backup completed
- [ ] Team notified of breaking changes

## Quick Steps

```bash
git pull origin main
./scripts/deploy.sh
curl https://api.example.com/health   # verify
```

## Detailed Steps

### 1. Pre-deployment
```bash
# Backup database
pg_dump production > backup_$(date +%s).sql
```

### 2. Deploy
```bash
git checkout main && git pull
./scripts/deploy.sh
```

### 3. Verify
```bash
curl https://api.example.com/health
# Expected: {"status":"ok"}
```

## Rollback

```bash
./scripts/rollback.sh <timestamp>
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Deploy fails | Check `tail -f /var/log/deploy.log` |
| Health check fails | Run `./scripts/rollback.sh` |

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Architecture](docs/ADR-NNN.md) | System design |
| [Operational Guide](docs/GUIDE-NNN-OPERATIONS.md) | Day-to-day operations |
```

**Rich example:** Load `references/deployment-example.md` for a Fly.io deployment with migrations.

---

## 5. Architecture Decision Record (ADR)

**Purpose:** Document important architectural decisions with context and rationale.  
**File:** `docs/ADR-NNN-DECISION_NAME.md`

**Required sections:** Problem, Options considered (≥2 with pros/cons), Decision + rationale, Consequences (good and bad), Related decisions.

```markdown
# ADR-NNN: Decision Title

**Status:** Accepted  
**Last Updated:** May 2026  
**Type:** ADR (Architecture Decision)  
**Author:** Name

---

## Problem

Why did this decision need to be made? What was forcing a choice?

## Options Considered

### Option 1: Approach name
**Pros:** Benefit 1, benefit 2  
**Cons:** Trade-off 1, trade-off 2

### Option 2: Approach name (Chosen)
**Pros:** Benefit 1, benefit 2  
**Cons:** Trade-off 1, trade-off 2

## Decision

**We chose Option 2.** Rationale in 2–4 sentences covering what tipped the scales.

## Consequences

**Good:**
- ✅ Benefit that follows from this choice
- ✅ Second benefit

**Bad:**
- ⚠️ Trade-off we accepted
- ⚠️ Second trade-off

## Related Documentation

| Document | Purpose |
|----------|---------|
| [ADR-NNN](ADR-NNN.md) | Related decision this depends on |
| [SPEC-NNN](SPEC-NNN.md) | Spec that implements this decision |
```

**Rich example:** Load `references/adr-example.md` for a PostgreSQL vs Neo4j decision with comparison table.

---

## 6. Operational Guide (Day-to-Day Reference)

**Purpose:** Quick reference for day-to-day tasks and incident response.  
**File:** `docs/GUIDE-NNN-OPERATIONS.md` or `docs/RUN-NNN-RUNBOOK.md`

**Required sections:** Quick reference table, Common tasks with copy-paste commands, Monitoring & alerts, Troubleshooting table, Escalation path.

```markdown
# Operational Guide: [System Name]

**Last Updated:** May 2026  
**Type:** GUIDE (Operational)  
**On-call:** @oncall-handle  
**Escalation:** Page after 5 min unresolved

---

## Quick Reference

| Task | Command | Time |
|------|---------|------|
| Check health | `curl https://api.example.com/health` | 10s |
| View logs | `tail -f /var/log/app.log` | 5s |
| Restart service | `systemctl restart app` | 2 min |

## Common Tasks

### 1. Check service health
```bash
curl -s https://api.example.com/health | jq .
# Expected: {"status":"ok"}
```

### 2. Restart service
```bash
systemctl restart app
systemctl status app   # verify running
```

## Monitoring & Alerts

| Metric | Normal | Alert | Action |
|--------|--------|-------|--------|
| CPU | <50% | >80% | Check processes; restart if stuck |
| Error rate | <0.1% | >1% | Page oncall immediately |
| Response time | <200ms | >500ms | Check slow queries |

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 502 Bad Gateway | Backend down | Restart service |
| Database timeout | Connection pool exhausted | Restart; check for leaks |

## Escalation

```
Issue → Can fix in 5 min? → Fix and document in #incidents
       → Can't fix?       → Page @oncall
       → Stuck 10 min?    → Page manager + incident commander
```

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Deployment Guide](docs/RUN-NNN-DEPLOY.md) | How to deploy new versions |
| [Architecture](docs/ADR-NNN.md) | System design overview |
```

**Rich example:** Load `references/operational-example.md` for a Fly.io backend ops guide with Grafana monitoring.

---

## Best Practices

### Every Doc Must Include
- `**Status:**` and `**Last Updated:**` in the first 5 lines after the title
- `**Type:**` specifying the doc category (GUIDE, SPEC, ADR, RUN, REPORT)
- At least one quick-reference table or quick-steps section
- `## Related Documentation` table at the bottom with 2–5 cross-references

### Tables
- Max 5 columns; sort by importance, not alphabetically
- Use status symbols instead of long text (✅ beats "complete and working")

### Code Blocks
- Always specify language: ` ```bash `, ` ```python `, ` ```sql `
- Include expected output as comments where helpful

### Links
- Always descriptive: `[SPEC-015 Agentic Workflow](path)` not `[link](path)`
- Cross-reference format: `| [DOC-NNN Title](path) | One-line description |`

---

## Usage Examples

**README for a new project:**
> "Create a README for my data pipeline project"  
→ Produces `README.md` with Features table, Quick Start, and Documentation index in ai-companions style

**Feature specification:**
> "Write a spec for our new Redis caching layer"  
→ Creates `docs/SPEC-NNN-REDIS_CACHING.md` with problem statement, architecture, data model, and trade-offs table

**Architecture decision:**
> "Document our decision to use PostgreSQL instead of MongoDB"  
→ Creates `docs/ADR-NNN-POSTGRESQL_VS_MONGODB.md` with options, decision rationale, and consequences

**Deployment runbook:**
> "Write deployment steps for our Kubernetes cluster"  
→ Creates `docs/RUN-NNN-KUBERNETES_DEPLOY.md` with prerequisites checklist, quick steps, rollback, and troubleshooting

**Operational guide:**
> "Create an operations runbook for our API service"  
→ Creates `docs/GUIDE-NNN-OPERATIONS.md` (or `docs/RUN-NNN-RUNBOOK.md`) with quick reference, monitoring alerts, and escalation path

**Status report:**
> "Write a Q1 project status report"  
→ Creates `docs/REPORT-NNN-Q1_STATUS.md` with summary table, completed work, blockers, and next steps
