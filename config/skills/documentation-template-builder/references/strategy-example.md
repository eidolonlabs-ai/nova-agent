# STRATEGY-001: Product Strategy — H2 2026

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** STRATEGY (Product Strategy)  
**Author:** Alex Chen, Head of Product  
**Approved by:** CEO, Engineering Lead  
**Review cycle:** Quarterly (next review: August 2026)

---

## Vision

> Every team ships better software because product decisions are written down, shared, and connected.

**Mission:** Build the documentation layer for product teams — from PRD to release notes — so knowledge doesn't live in Slack or people's heads.

**North Star metric:** Documents actively referenced during sprint planning (weekly)  
**Current value:** 1.2 docs/team/sprint | **Target:** 4.0 docs/team/sprint by Dec 31, 2026

---

## Strategic Context

**Why this matters now:**
- Teams that write PRDs ship 30% fewer rework cycles (internal cohort study, Q4 2025)
- 68% of churned customers cited "hard to onboard new team members" as a top-3 reason (exit interviews, Q1 2026)
- Competitors (Notion, Linear) offer document storage but no document intelligence — no templates, no cross-referencing, no quality feedback
- We have 5,400 active teams; only 12% use more than 3 doc types. This is the growth lever.

**Where we are today:**

| Dimension | Today (May 2026) | H2 Target (Dec 2026) |
|-----------|-----------------|----------------------|
| DAU | 8,400 | 18,000 |
| ARR | $1.2M | $3.0M |
| Teams tier adoption | 18% of customers | 40% of customers |
| Docs/team/sprint | 1.2 | 4.0 |
| NPS | 42 | 55 |

---

## Strategic Bets

### Bet 1: Templates drive habit formation
**Hypothesis:** If we give teams pre-built, connected templates (PRD → SPEC → PERSONA → RELEASE), they will create 3× more documents and embed documentation into their existing workflow within 60 days.

**Why we believe this:** The 12% of teams who use 3+ doc types have 4× higher retention and 2× higher NPS. The barrier is the blank page, not intent.

**Key initiatives:**
- [PRD-008: Documentation Template Suite](../PRD-008-DOC_TEMPLATE_SUITE.md) — 10 templates, all cross-linked
- [PRD-009: Smart Doc Suggestions](../PRD-009-SMART_SUGGESTIONS.md) — AI suggests next doc to create based on workflow stage

**Success signal:** Average docs/team/sprint reaches 3.0 by October 2026

---

### Bet 2: Real-time collaboration unlocks Teams tier upsell
**Hypothesis:** If simultaneous editing is fast and conflict-free, solo users will pull in a second teammate, converting Free → Teams at a 20% higher rate.

**Why we believe this:** 61% of Free users who tried sharing a document with a teammate upgraded within 30 days (product analytics, Q1 2026). The friction is the collaboration experience, not the price.

**Key initiatives:**
- [PRD-007: Real-Time Collab (shipped v2.3.0)](../PRD-007-REALTIME_COLLAB.md) ✅
- [PRD-010: Presence & Activity Feed](../PRD-010-PRESENCE.md) — shows what teammates did while you were away

**Success signal:** Free → Teams conversion rate increases from 8% to 15% by September 2026

---

### Bet 3: Onboarding new team members is the enterprise wedge
**Hypothesis:** If onboarding a new engineer or PM to a team means reading living docs (not asking Slack questions), enterprises will pay for per-seat Teams licenses at higher ACV.

**Why we believe this:** Top enterprise request (14/20 enterprise interviews): "We need new hires to get productive in week 1, not month 2." Documentation is the unlock.

**Key initiatives:**
- [PRD-011: Team Knowledge Graph](../PRD-011-KNOWLEDGE_GRAPH.md) — auto-links related docs, surfaces relevant context
- [PRD-012: Onboarding Checklist](../PRD-012-ONBOARDING.md) — PM creates a "start here" reading list for new hires

**Success signal:** Enterprise ACV increases from $8K to $14K; 3 new enterprise logos in H2

---

## OKRs — H2 2026

### Objective 1: Make documentation a daily habit for product teams

| Key Result | Owner | Target | Status |
|------------|-------|--------|--------|
| KR1: Docs/team/sprint reaches 4.0 (from 1.2) | Product | Dec 31 | 🟡 1.4 currently |
| KR2: 50% of new PRDs use a template (from 8%) | Product | Oct 31 | 📋 Not started |
| KR3: Template library ships 10 doc types | Eng | Aug 15 | 🟡 7 types exist |

### Objective 2: Grow Teams tier to 40% of customer base

| Key Result | Owner | Target | Status |
|------------|-------|--------|--------|
| KR1: Free → Teams conversion rate reaches 15% | Product | Sep 30 | 🟡 9% currently |
| KR2: Real-time collab DAU reaches 3,000 | Eng | Sep 30 | 📋 Launched May 20 |
| KR3: NPS reaches 55 (from 42) | Product | Dec 31 | 🟡 44 in May survey |

### Objective 3: Land 3 enterprise customers at $12K+ ACV

| Key Result | Owner | Target | Status |
|------------|-------|--------|--------|
| KR1: Knowledge Graph beta with 5 enterprise pilots | Eng | Sep 15 | 📋 Design starts Jun 1 |
| KR2: 3 enterprise logos signed | Sales | Dec 31 | 📋 2 in pipeline |
| KR3: Enterprise churn rate stays below 5% | CS | Dec 31 | ✅ 3% currently |

---

## What We Are NOT Doing (H2 2026)

Being explicit about trade-offs is as important as what we build.

- **Not building a mobile app** — our users are desktop-first; mobile is a H1 2027 bet after we validate enterprise
- **Not localizing to non-English markets** — requires support, legal, and ops investment we're not ready for
- **Not adding video or audio to documents** — Loom and Notion already own this; we're not competing there
- **Not building a public template marketplace** — too early; first ensure our own 10 templates are excellent
- **Not chasing the bottom of the market (Free tier features)** — conversion rate is our metric, not Free DAU

---

## How to Use This Document

- **Prioritization:** When a new feature request comes in, check which Bet it supports. No fit = no H2 roadmap.
- **PRD alignment:** Every PRD must cite the Bet it supports in its Overview section.
- **Stakeholder communication:** Send this to execs each quarter with updated OKR status.
- **Team alignment:** Review Bets in sprint planning kick-offs — make sure engineers understand the "why" behind what they're building.

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [GUIDE-NNN Roadmap H2 2026](GUIDE-NNN-ROADMAP_H2_2026.md) | Quarterly execution plan with sprint-level detail |
| [REPORT-001 Q1 2026 Status](REPORT-001-Q1_2026_STATUS.md) | Most recent project status snapshot |
| [PRD-008 Doc Template Suite](PRD-008-DOC_TEMPLATE_SUITE.md) | Primary initiative for Bet 1 |
| [PRD-007 Real-Time Collab](PRD-007-REALTIME_COLLAB.md) | Delivered initiative for Bet 2 |
| [PERSONA-001 Startup PM](PERSONA-001-STARTUP_PM.md) | Primary user this strategy serves |
