---
name: documentation-template-builder
category: development
description: Generate project documentation in ai-companions style — README, roadmap, GUIDE, SPEC, ADR, RUN, PRD (product requirements), PERSONA (user personas), RELEASE (release notes), STRATEGY (product strategy/vision), RESEARCH (competitive analysis), GTM (go-to-market/launch plan), REPORT (status report). Use when creating, writing, or updating any project docs. Produces complete markdown with status indicators (✅🟡📋), quick reference tables, and Related Documentation sections. In nova-agent projects, files live in docs/ with prefixes GUIDE-NNN, SPEC-NNN, ADR-NNN, RUN-NNN, PRD-NNN, PERSONA-NNN, RELEASE-NNN, STRATEGY-NNN, RESEARCH-NNN, GTM-NNN, REPORT-NNN.
---

# Documentation Template Builder

Generate professional project documentation in ai-companions style: status symbols, quick reference tables, cross-referenced structure, and complete content (not just empty scaffolding).

**Rich examples available.** Load any of these via `read_file` when you need a detailed reference:
- `{skill_dir}/references/readme-example.md`
- `{skill_dir}/references/roadmap-example.md`
- `{skill_dir}/references/spec-example.md`
- `{skill_dir}/references/deployment-example.md`
- `{skill_dir}/references/adr-example.md`
- `{skill_dir}/references/operational-example.md`
- `{skill_dir}/references/prd-example.md`
- `{skill_dir}/references/persona-example.md`
- `{skill_dir}/references/release-notes-example.md`
- `{skill_dir}/references/strategy-example.md`
- `{skill_dir}/references/competitive-analysis-example.md`
- `{skill_dir}/references/gtm-plan-example.md`

---

## Nova-Agent File Naming Conventions

All docs live in `docs/`. Use the correct type prefix and sequence number:

| Type | Pattern | When to use |
|------|---------|-------------|
| Feature/usage guide | `GUIDE-NNN-NAME.md` | How-to docs, developer references |
| Product requirements | `PRD-NNN-NAME.md` | Feature requirements, user stories, acceptance criteria |
| User personas | `PERSONA-NNN-NAME.md` | Who we're building for — goals, frustrations, behaviors |
| Specification | `SPEC-NNN-NAME.md` | Feature design, data models, APIs |
| Architecture decision | `ADR-NNN-NAME.md` | Design decisions and rationale |
| Deployment/runbook | `RUN-NNN-NAME.md` | Step-by-step operational procedures |
| Release notes | `RELEASE-NNN-NAME.md` | Customer-facing changelog for a version |
| Product strategy | `STRATEGY-NNN-NAME.md` | Vision, bets, OKRs, long-term direction |
| Competitive analysis | `RESEARCH-NNN-NAME.md` | Market landscape, competitor teardowns, positioning |
| Go-to-market plan | `GTM-NNN-NAME.md` | Launch coordination across PM, Marketing, CS |
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

## 7. Product Requirements Document (PRD)

**Purpose:** Define feature requirements, user stories, acceptance criteria, and success metrics before engineering begins.  
**File:** `docs/PRD-NNN-FEATURE_NAME.md`

**Required sections:** Overview/problem statement, Target users, User stories with acceptance criteria, Success metrics, Constraints & assumptions, Out of scope, Related documentation.

```markdown
# PRD-NNN: Feature Name

**Status:** ✅ Approved  
**Last Updated:** May 2026  
**Type:** PRD (Product Requirements)  
**Author:** Product Manager  
**Stakeholders:** Engineering Lead, Design Lead, Customer Success

---

## Overview

**Problem:** What user problem does this feature solve?

**Solution:** One-sentence summary of what we're building.

**Impact:** Why this matters to the business (user retention, revenue, competitive advantage).

---

## Target Users

| User Type | Need | Priority |
|-----------|------|----------|
| User type 1 | What they need to do | P0/P1/P2 |
| User type 2 | What they need to do | P0/P1/P2 |

---

## User Stories & Acceptance Criteria

### Story 1: User action
**As a** [user type], **I want to** [action] **so that** [benefit].

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

**Notes:** Any edge cases or special handling.

### Story 2: User action
**As a** [user type], **I want to** [action] **so that** [benefit].

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

---

## Success Metrics

| Metric | Target | Owner | Measurement |
|--------|--------|-------|-------------|
| User adoption | >50% within 90d | Product | Analytics dashboard |
| Feature usage | >1000 DAU | Product | Event tracking |
| Customer satisfaction | >4.0/5.0 CSAT | CS | Post-launch survey |

---

## Constraints & Assumptions

**Constraints:**
- Must work on mobile and desktop
- No breaking changes to existing APIs
- Budget: 4 weeks of engineering

**Assumptions:**
- Users have stable internet connection
- User base grows 10% monthly
- No major platform changes in scope window

---

## Out of Scope

- [ ] Mobile app redesign (handled in separate PRD)
- [ ] Premium tier features (future phase)
- [ ] Internationalization (phase 2)

---

## Timeline

| Phase | Dates | Deliverable |
|-------|-------|-------------|
| Design | May 15–22 | Mockups, spec |
| Engineering | May 23–Jun 15 | Code, tests, docs |
| QA & launch | Jun 16–20 | Testing, release |

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [SPEC-NNN](docs/SPEC-NNN.md) | Detailed technical specification |
| [Design Mockups](url) | Figma designs and interaction flows |
| [Market Research](url) | User interviews and competitive analysis |
```

**Rich example:** Load `references/prd-example.md` for a collaborative feature PRD with detailed user personas and metrics.

---

## 8. User Personas

**Purpose:** Define who you're building for — goals, frustrations, behaviors, and context — so every PRD and design decision references a shared understanding of the user.  
**File:** `docs/PERSONA-NNN-ROLE_NAME.md`

**Required sections:** Persona overview card, Goals & motivations, Frustrations & pain points, Behaviors & context, Quotes (from research), What success looks like, Related docs.

```markdown
# PERSONA-NNN: Persona Name

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** PERSONA (User Persona)  
**Based on:** [N] customer interviews, [N] survey responses

---

## Overview

| Attribute | Detail |
|-----------|--------|
| **Role** | Job title / role |
| **Age range** | e.g. 28–42 |
| **Technical level** | Beginner / Intermediate / Expert |
| **Team size** | Solo / Small team / Enterprise |
| **Primary device** | Desktop / Mobile / Both |

> One-sentence summary of who this person is and what they're trying to accomplish.

---

## Goals & Motivations

- **Primary goal:** What they're ultimately trying to achieve
- **Secondary goal:** Supporting objective
- **Success looks like:** How they know they've won

---

## Frustrations & Pain Points

- **P0 — Critical:** Pain that blocks them entirely (current workaround is painful)
- **P1 — Significant:** Pain that slows them down regularly
- **P2 — Minor:** Annoyance that they've accepted but would gladly fix

---

## Behaviors & Context

**How they work:**
- Describe their typical workflow, tools they use, environment
- When during the day/week they encounter this problem
- How they currently solve it (workarounds, competitor tools)

**What they care about most:**
- Speed / reliability / cost / simplicity / team features

---

## Representative Quotes

> "I spend two hours every Monday doing X manually — there has to be a better way."

> "The hardest part is when Y happens and I have no visibility into Z."

---

## What Success Looks Like

| Before (today) | After (with our product) |
|---------------|--------------------------|
| Takes 2 hours manually | Done in 10 minutes |
| Error-prone, no audit trail | Reliable, fully logged |
| No visibility for team | Dashboard for everyone |

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [PRD-NNN Feature Name](PRD-NNN.md) | Feature that addresses this persona's P0 pain |
| [PERSONA-NNN Related Role](PERSONA-NNN.md) | Overlapping persona |
```

**Rich example:** Load `references/persona-example.md` for a fully researched "Startup PM" persona with quotes and workflow breakdown.

---

## 9. Release Notes

**Purpose:** Customer-facing announcement of what shipped in a version — what changed, what's new, and what to do if upgrading.  
**File:** `docs/RELEASE-NNN-vX_Y_Z.md` (or `CHANGELOG.md` at root for cumulative history)

**Required sections:** Version header + date, Summary of the release, New features, Improvements, Bug fixes, Breaking changes (if any), Upgrade notes, Known issues.

```markdown
# RELEASE-NNN: v2.3.0 — Release Name

**Status:** ✅ Released  
**Release Date:** May 15, 2026  
**Type:** RELEASE (Release Notes)  
**Affects:** All users / [specific tier or feature]

---

## Summary

Short paragraph (2–3 sentences) describing what this release is about and the main theme. Example: "v2.3.0 focuses on collaboration — real-time co-editing, live presence indicators, and faster conflict resolution. It also fixes three critical bugs reported by enterprise customers."

---

## What's New

### Feature Name
Brief description of the feature and its value.  
→ [Learn more](docs/GUIDE-NNN-FEATURE.md)

### Feature Name 2
Brief description.  
→ [Documentation](docs/GUIDE-NNN-FEATURE2.md)

---

## Improvements

- **Performance:** Describe the improvement and impact (e.g. "Search results load 3× faster")
- **UI:** What changed visually and why it's better
- **Reliability:** Error reduction, uptime improvement

---

## Bug Fixes

| Issue | Affected | Fixed in |
|-------|----------|---------|
| Brief description of bug | Which users / features | v2.3.0 |
| Brief description of bug | Which users / features | v2.3.0 |

---

## Breaking Changes

> ⚠️ **Action required before upgrading**

- **API change:** `old_method()` removed — use `new_method()` instead ([migration guide](docs/GUIDE-NNN-MIGRATION.md))
- **Config change:** `config.old_key` renamed to `config.new_key`

If no breaking changes: *No breaking changes in this release.*

---

## Upgrade Notes

```bash
pip install --upgrade your-package
# or
nova upgrade
```

Run migrations if applicable:
```bash
your-tool migrate
```

---

## Known Issues

| Issue | Workaround | Fix target |
|-------|------------|-----------|
| Brief description | Temporary workaround | v2.3.1 |

If none: *No known issues.*

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [RELEASE-NNN v2.2.0](RELEASE-NNN.md) | Previous release |
| [Migration Guide](docs/GUIDE-NNN-MIGRATION.md) | Upgrade instructions for breaking changes |
| [CHANGELOG.md](../../CHANGELOG.md) | Full version history |
```

**Rich example:** Load `references/release-notes-example.md` for a v2.3.0 release with new features, breaking API changes, and migration instructions.

---

## 10. Product Strategy / Vision

**Purpose:** Articulate the long-term direction, strategic bets, and OKRs that guide prioritization decisions across teams and quarters.  
**File:** `docs/STRATEGY-NNN-YEAR_OR_THEME.md`

**Required sections:** Vision statement, Strategic context (why now), Bets / themes, OKRs, What we're NOT doing, How to use this doc.

```markdown
# STRATEGY-NNN: Product Strategy — [Year/Theme]

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** STRATEGY (Product Strategy)  
**Author:** Head of Product  
**Review cycle:** Quarterly

---

## Vision

> One sentence: what does the world look like when we succeed?

**Mission:** What we do, for whom, and why it matters.

**North Star metric:** The single number that proves we're succeeding.  
**Current value:** X | **Target:** Y by [date]

---

## Strategic Context

**Why this matters now:**
- Market shift or trend (data point)
- Customer signal (quote or stat from research)
- Competitive pressure or opportunity

**Where we are today:**
| Dimension | Today | Goal |
|-----------|-------|------|
| Users | N DAU | X DAU |
| Revenue | $Xk ARR | $Yk ARR |
| NPS | N | X |

---

## Strategic Bets

### Bet 1: Theme Name
**Hypothesis:** If we [do X], then [Y users] will [achieve Z], which drives [north star metric].  
**Key initiatives:** PRD-NNN, PRD-NNN  
**Success signal:** Metric or milestone that validates this bet

### Bet 2: Theme Name
**Hypothesis:** ...  
**Key initiatives:** PRD-NNN, PRD-NNN  
**Success signal:** ...

### Bet 3: Theme Name
**Hypothesis:** ...  
**Key initiatives:** PRD-NNN  
**Success signal:** ...

---

## OKRs

### Objective 1: [Outcome statement]
| Key Result | Owner | Target | Current |
|------------|-------|--------|---------|
| KR1: Metric | Team | Value by date | 🟡 Current |
| KR2: Metric | Team | Value by date | 📋 Not started |

### Objective 2: [Outcome statement]
| Key Result | Owner | Target | Current |
|------------|-------|--------|---------|
| KR1: Metric | Team | Value by date | ✅ Done |
| KR2: Metric | Team | Value by date | 🟡 In progress |

---

## What We Are NOT Doing (This Cycle)

Being explicit about trade-offs is as important as what we prioritize.

- **Not doing:** X — because it's lower leverage than Bet 2 right now
- **Not doing:** Y — we'll revisit in H2
- **Not doing:** Z — this is a founder-led decision, not product's

---

## How to Use This Document

- **Prioritization:** When asked why something isn't on the roadmap, point here
- **PRD alignment:** Every PRD should cite which strategic bet it supports
- **Stakeholder communication:** Share to align execs and cross-functional leads

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Roadmap](docs/GUIDE-NNN-ROADMAP.md) | Quarterly execution plan |
| [REPORT-NNN Status](docs/REPORT-NNN.md) | Progress against OKRs |
| [PRD-NNN Key Feature](docs/PRD-NNN.md) | Primary initiative for Bet 1 |
```

**Rich example:** Load `references/strategy-example.md` for a full H2 strategy doc with three bets, OKRs, and explicit trade-offs.

---

## 11. Competitive Analysis (RESEARCH)

**Purpose:** Map the competitive landscape, identify where competitors are strong and weak, and derive positioning implications for your product.  
**File:** `docs/RESEARCH-NNN-COMPETITIVE_ANALYSIS.md`

**Required sections:** TL;DR positioning statement, competitors overview table, per-competitor teardown (strengths/weaknesses/pricing), feature comparison matrix, positioning gaps, strategic implications.

```markdown
# RESEARCH-NNN: Competitive Analysis — [Market / Category]

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** RESEARCH (Competitive Analysis)  
**Author:** Product Manager  
**Next review:** Quarterly (markets shift fast)

---

## TL;DR

> One paragraph: what this market looks like, who the key players are, and where our strongest differentiation sits.

**Our positioning:** We win when [ideal scenario]. We lose when [weak scenario].

---

## Competitors Overview

| Competitor | Segment | Pricing | Strength | Key weakness |
|------------|---------|---------|----------|--------------|
| Competitor A | Enterprise | $X/seat/mo | Strength | Weakness |
| Competitor B | SMB | $Y/mo flat | Strength | Weakness |
| Competitor C | Developer | Freemium | Strength | Weakness |
| Us | [segment] | $Z/mo | Strength | Current gap |

---

## Competitor Teardowns

### Competitor A

**Overview:** 2–3 sentence summary of what they do and who they target.

**Strengths:**
- ✅ Specific strength with evidence
- ✅ Specific strength with evidence

**Weaknesses:**
- 🔴 Specific weakness (source: customer interviews / reviews / personal testing)
- 🔴 Specific weakness

**Pricing:** Free tier / $X starter / $Y pro / $Z enterprise  
**Notable customers:** Company A, Company B  
**Key differentiator vs. us:** One sentence on the core battle.

---

### Competitor B

**Overview:** ...

**Strengths:**
- ✅ ...

**Weaknesses:**
- 🔴 ...

**Pricing:** ...  
**Key differentiator vs. us:** ...

---

## Feature Comparison Matrix

| Feature | Us | Competitor A | Competitor B | Competitor C |
|---------|-----|-------------|-------------|-------------|
| Feature 1 | ✅ | ✅ | ❌ | 🟡 Partial |
| Feature 2 | ✅ | ❌ | ✅ | ❌ |
| Feature 3 | 📋 Planned | ✅ | ✅ | ✅ |
| Feature 4 | ✅ | ❌ | ❌ | ❌ |

Legend: ✅ Full support · 🟡 Partial · ❌ Not available · 📋 Planned

---

## Positioning Gaps

**Where we are clearly ahead:**
- Feature / capability where no competitor matches us

**Where we are at parity:**
- Table stakes features we must maintain but don't win on

**Where we are behind (and it matters):**
- Gap with Competitor A in [area] — affects [which customers]; close by [date] with [PRD-NNN]

**Where we choose not to compete:**
- Capability we've deliberately skipped and why

---

## Strategic Implications

| Insight | Action | Owner | Priority |
|---------|--------|-------|----------|
| Competitor A's weakness in X is our window | Accelerate PRD-NNN to close before they ship | PM | P0 |
| Feature Y is now table stakes (all competitors have it) | Add to roadmap H2 | PM | P1 |
| Competitor B is moving up-market | Defend SMB with pricing adjustment | Business | P1 |

---

## Sources

- Customer interviews: [N] customers asked about alternatives (date)
- G2 / Capterra reviews: analyzed top 20 reviews per competitor (date)
- Personal product testing: [date]
- Pricing pages: checked [date] — verify quarterly

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [STRATEGY-NNN H2 Strategy](STRATEGY-NNN.md) | Strategic bets informed by this analysis |
| [PRD-NNN Feature to close gap](PRD-NNN.md) | Feature addressing top competitive gap |
| [PERSONA-NNN Primary user](PERSONA-NNN.md) | User persona for whom these trade-offs matter most |
```

**Rich example:** Load `references/competitive-analysis-example.md` for a document-tool market teardown with feature matrix and strategic implications.

---

## 12. Go-to-Market Plan (GTM)

**Purpose:** Coordinate every function — PM, Marketing, Sales, CS, Docs — around a feature or product launch so nothing falls through the cracks.  
**File:** `docs/GTM-NNN-FEATURE_NAME.md`

**Required sections:** Launch summary, target audience + messaging, launch tiers (internal / beta / GA), readiness checklist per function, timeline, success metrics, rollback plan.

```markdown
# GTM-NNN: Launch Plan — [Feature or Product Name]

**Status:** 🟡 In Progress  
**Launch Date:** May 30, 2026  
**Type:** GTM (Go-to-Market Plan)  
**Author:** Product Manager  
**Stakeholders:** Marketing, Sales, CS, Docs, Engineering

---

## Launch Summary

| Attribute | Detail |
|-----------|--------|
| **What's launching** | One-sentence description of the feature |
| **Who it's for** | Target user segment (link to persona) |
| **Launch tier** | Limited beta / Closed beta / GA |
| **Launch date** | May 30, 2026 |
| **Primary metric** | What we'll measure to declare success |

---

## Target Audience & Messaging

**Primary audience:** [PERSONA-NNN link] — what they care about most

**Core message (one sentence):**
> "Now you can [do X] without [pain Y] — [product name] makes it [fast/simple/reliable]."

**Supporting messages:**
- For users: How this saves them time / reduces frustration
- For buyers/decision-makers: Business impact, ROI, risk reduction
- For technical users: How it works, integration points

**What to avoid saying:**
- Internal jargon that users don't recognize
- Competitor names (unless approved by legal)

---

## Launch Tiers

### Tier 0: Internal (T-14 days — May 16)
- [ ] Dog-food with internal team for 1 week
- [ ] Collect internal feedback; fix critical bugs
- [ ] Finalize help docs draft

### Tier 1: Limited Beta (T-7 days — May 23)
- [ ] Invite 10–20 design partners / power users
- [ ] Beta label in UI; feedback widget enabled
- [ ] Monitor error rates and latency daily

### Tier 2: General Availability (May 30)
- [ ] Feature flag flipped for all users
- [ ] Announcement blog post published
- [ ] Email campaign sent to full user base
- [ ] In-app announcement banner live

---

## Readiness Checklist

### Product & Engineering
- [ ] Feature complete and passing QA
- [ ] Performance verified (<200ms latency p99)
- [ ] Feature flag wired and tested (off → on → off)
- [ ] Error monitoring configured (Datadog / Sentry alert)
- [ ] Rollback procedure documented and tested

### Marketing
- [ ] Blog post written and reviewed (draft link: ___)
- [ ] Email campaign copy approved (send date: ___)
- [ ] Social posts scheduled (Twitter/LinkedIn, launch day)
- [ ] Product Hunt listing prepared (if applicable)
- [ ] Screenshots / GIFs / demo video ready

### Sales & CS
- [ ] Sales brief sent to AEs (feature summary, objections, pricing impact)
- [ ] CS team trained on new feature (date: ___)
- [ ] FAQ doc ready for customer questions
- [ ] Known issues + workarounds documented for CS

### Documentation
- [ ] Help center article published
- [ ] In-app tooltips / onboarding flow updated
- [ ] RELEASE-NNN release notes drafted
- [ ] API docs updated (if applicable)

---

## Timeline

| Date | Milestone | Owner | Status |
|------|-----------|-------|--------|
| May 9 | Feature complete | Engineering | ✅ Done |
| May 16 | Internal dog-food begins | PM | 🟡 In progress |
| May 20 | Beta invites sent | PM | 📋 Planned |
| May 23 | Beta live | Engineering | 📋 Planned |
| May 27 | Blog post + email finalized | Marketing | 📋 Planned |
| May 30 | GA launch | PM | 📋 Planned |
| Jun 13 | 2-week post-launch review | PM | 📋 Planned |

---

## Success Metrics

| Metric | Target | Measurement | Review date |
|--------|--------|-------------|-------------|
| Adoption (% of DAU using feature) | >20% in 30d | Analytics | Jun 30 |
| Activation (users who complete core action) | >60% of adopters | Funnel tracking | Jun 30 |
| CSAT / NPS delta | +5 NPS vs. baseline | In-app survey | Jun 30 |
| Support tickets on this feature | <5/week | Zendesk | Weekly |

---

## Risks & Rollback

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Error spike at GA | Medium | Feature flag off within 15 min; alert threshold set |
| Low adoption | Medium | In-app onboarding prompt if user hasn't tried after 7d |
| Negative press / social | Low | CS on standby; comms response drafted |

**Rollback trigger:** Error rate >1% sustained for 5 min → disable feature flag → post status update → page on-call.

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [PRD-NNN Feature Requirements](PRD-NNN.md) | Full requirements behind this launch |
| [RELEASE-NNN Release Notes](RELEASE-NNN.md) | Customer-facing release notes |
| [PERSONA-NNN Primary User](PERSONA-NNN.md) | Target user for messaging |
| [RESEARCH-NNN Competitive Context](RESEARCH-NNN.md) | Market positioning this launch supports |
```

**Rich example:** Load `references/gtm-plan-example.md` for a real-time collaboration GA launch with per-function readiness checklists and rollback plan.

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

**Product requirements:**
> "Write a PRD for our new collaborative editing feature"  
→ Creates `docs/PRD-NNN-COLLABORATIVE_EDITING.md` with user stories, acceptance criteria, success metrics, and timeline

**User personas:**
> "Create a persona for our power user — a startup PM who manages roadmaps solo"  
→ Creates `docs/PERSONA-NNN-STARTUP_PM.md` with goals, pain points, workflow context, and representative quotes

**Release notes:**
> "Write release notes for v2.3.0 — we shipped real-time collab and fixed two critical bugs"  
→ Creates `docs/RELEASE-NNN-v2_3_0.md` with new features, bug fix table, breaking changes, and upgrade instructions

**Product strategy:**
> "Write our H2 2026 product strategy doc with our three bets and OKRs"  
→ Creates `docs/STRATEGY-NNN-H2_2026.md` with vision, strategic bets, OKR table, and explicit trade-offs

**Competitive analysis:**
> "Do a competitive analysis of our document collaboration market — Notion, Confluence, Google Docs"  
→ Creates `docs/RESEARCH-NNN-COMPETITIVE_ANALYSIS.md` with competitor teardowns, feature matrix, positioning gaps, and strategic implications

**Go-to-market plan:**
> "Write a GTM plan for our v2.3.0 real-time collaboration launch on May 30"  
→ Creates `docs/GTM-NNN-REALTIME_COLLAB_LAUNCH.md` with readiness checklists per function, launch tiers, timeline, and rollback trigger

**Status report:**
> "Write a Q1 project status report"  
→ Creates `docs/REPORT-NNN-Q1_STATUS.md` with summary table, completed work, blockers, and next steps
