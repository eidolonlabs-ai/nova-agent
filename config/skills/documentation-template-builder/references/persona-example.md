# PERSONA-001: The Startup PM

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** PERSONA (User Persona)  
**Based on:** 12 customer interviews, 38 survey responses (Q1 2026)

---

## Overview

| Attribute | Detail |
|-----------|--------|
| **Role** | Product Manager at an early-stage startup (Series A or earlier) |
| **Age range** | 28–38 |
| **Technical level** | Intermediate — reads code, can't write it without help |
| **Team size** | 2–6 engineers, 1 designer, no dedicated PM support |
| **Primary device** | MacBook (desktop-first), iPhone for async check-ins |

> Alex is a solo PM at a 12-person startup who owns the entire product surface: roadmap, PRDs, customer interviews, stakeholder communication, and release coordination — all at once.

---

## Goals & Motivations

- **Primary goal:** Ship the right features fast enough to hit the next funding milestone
- **Secondary goal:** Build a scalable product process before the team grows past 15 people
- **Tertiary goal:** Earn engineering trust by writing clear, unambiguous requirements
- **Success looks like:** Features shipped on time, low rework rate, engineers feel unblocked

---

## Frustrations & Pain Points

- **P0 — Critical:** Writing PRDs from scratch each time takes 3–5 hours; no template, no consistency
- **P0 — Critical:** Context gets lost between docs — engineers ask questions PRDs should have answered
- **P1 — Significant:** Release notes are always written at the last minute and lack detail customers need
- **P1 — Significant:** No single source of truth for product strategy — decisions are made in Slack threads
- **P2 — Minor:** User personas exist in a founder's head, never written down, so new hires make wrong assumptions
- **P2 — Minor:** ADRs and SPECs are inconsistently formatted; hard to onboard new engineers

---

## Behaviors & Context

**How they work:**
- Writes PRDs in Notion, Google Docs, or Markdown — whichever the team already uses
- Runs weekly product syncs: 15 min standup, 30 min roadmap review
- Does customer calls every other week; takes messy notes that rarely get distilled
- Reviews pull requests for product correctness, not code quality
- Sends weekly "what shipped" Slack messages; no formal release notes process

**When they encounter this problem:**
- Monday morning: planning the sprint and realizing last week's decisions are undocumented
- Before engineering kickoff: scrambling to write requirements in 2 hours that should take 2 days
- Post-launch: trying to write customer-facing release notes from a git log

**Current workarounds:**
- Copy-pastes old PRDs and manually strips irrelevant sections
- Uses ChatGPT to draft release notes from bullet points
- Relies on engineers to remember decisions from Slack ("just ask Jordan, he knows")

**Tools they use:**
- Linear or Jira (tickets), Notion or Confluence (docs), Figma (designs), Slack (everything else)
- GitHub for reading PRs; Datadog or Mixpanel for metrics

---

## Representative Quotes

> "I know what needs to get built, but I spend half my time writing about it instead of figuring out what to build next."

> "Every PRD I write looks different. My engineers have to re-learn where to find the acceptance criteria each time."

> "I wrote a strategy doc once. It lived in Notion for a month and then everyone forgot about it. I don't know how to make these things stick."

> "Release notes are the thing I always do poorly. I write them in 20 minutes right before launch and customers can tell."

---

## What Success Looks Like

| Before (today) | After (with consistent docs) |
|---------------|------------------------------|
| PRD takes 3–5 hours, inconsistent format | PRD takes 60–90 min with templates, engineers know where to look |
| Strategy lives in Slack/memory | Single STRATEGY doc updated quarterly, referenced in every PRD |
| Release notes are an afterthought | Release notes drafted as feature ships; customer-ready in 20 min |
| Personas are tribal knowledge | Persona docs referenced in every PRD, updated after each research round |
| New engineers make wrong assumptions | Onboarding links to Persona-NNN; design decisions make sense immediately |

---

## Design Implications

- **Templates must be fast to fill in** — Alex doesn't have 5 hours, so sections must be scannable with clear prompts
- **Cross-referencing is key** — Alex needs to link PRD → PERSONA → SPEC without hunting across tools
- **Release notes need a "draft as you go" pattern** — not written at the end, but updated section by section during the sprint
- **Strategy must be actionable** — vision alone isn't enough; needs explicit "not doing" section to hold the line on scope

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [PERSONA-002: Enterprise Engineering Lead](PERSONA-002-ENTERPRISE_ENG_LEAD.md) | Related persona with different doc needs |
| [PRD-001: Document Templates](PRD-001-DOC_TEMPLATES.md) | Feature built for this persona's P0 pain |
| [STRATEGY-001: H2 2026](STRATEGY-001-H2_2026.md) | Strategic context this persona cares about most |
