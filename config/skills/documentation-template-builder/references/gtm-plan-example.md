# GTM-001: Launch Plan — Real-Time Collaboration (v2.3.0)

**Status:** 🟡 In Progress  
**Launch Date:** May 30, 2026  
**Type:** GTM (Go-to-Market Plan)  
**Author:** Alex Chen, Product Manager  
**Stakeholders:** Engineering (Sarah), Marketing (Jordan), CS (Jamie), Docs (Taylor)

---

## Launch Summary

| Attribute | Detail |
|-----------|--------|
| **What's launching** | Real-time collaborative editing with live cursors and conflict resolution |
| **Who it's for** | Teams on Pro and Teams tiers; primary persona: [PERSONA-001 Startup PM](PERSONA-001-STARTUP_PM.md) |
| **Launch tier** | General Availability — all Pro and Teams users |
| **Launch date** | May 30, 2026 |
| **Primary metric** | 20% of DAU using real-time collab within 30 days of launch |

---

## Target Audience & Messaging

**Primary audience:** Small product teams (2–6 people) who currently share documents via "share link" and manually reconcile edits. They've lost work to overwrites; they know they need real-time collaboration but assumed we didn't have it.

**Core message:**
> "Now your whole team can edit together — live, instant, and conflict-free. No more 'who has the latest version?'"

**Supporting messages:**
- **For users:** "See your teammates' cursors as they type. Changes appear in under 200ms. Works in every browser."
- **For decision-makers / team leads:** "Reduce the back-and-forth that slows down sprint planning. One doc, one source of truth, everyone in sync."
- **For technical evaluators:** "Operational transformation engine, WebSocket-backed, with full edit history and rollback."

**What to avoid:**
- Don't say "like Google Docs" — invites direct comparison we may not win on every dimension
- Don't lead with the technical implementation (OT, WebSockets) in non-technical messaging
- Avoid "beta" language in GA announcement — we shipped this, own it

---

## Launch Tiers

### Tier 0: Internal Dog-food (May 9–15) ✅ Complete
- [x] All internal documents migrated to real-time editing
- [x] Engineering team tested with 10 simultaneous editors
- [x] Three bugs caught and fixed (see [RELEASE-004](RELEASE-004-v2_3_0.md))
- [x] Internal feedback: "fast, cursors are delightful, conflict UI needs tooltip"

### Tier 1: Limited Beta (May 16–22) 🟡 In Progress
- [x] Invited 15 design partners (power users, Teams tier, active PRD writers)
- [x] Beta banner shown in UI: "You're in the real-time collab beta — share feedback"
- [ ] Collect structured feedback via in-app survey (closes May 21)
- [ ] Fix P0/P1 bugs from beta feedback before GA

**Beta feedback so far (May 18):**
- 11/15 partners rated experience 4+ stars
- Top request: "Show when a collaborator disconnects" (added to v2.3.1 backlog)
- One P1 bug: Firefox 124 conflict modal renders behind sidebar → fix in v2.3.1

### Tier 2: General Availability (May 30)
- [ ] Feature flag flipped for all Pro and Teams users
- [ ] Blog post live at 9am PT
- [ ] Email to full user base at 10am PT
- [ ] In-app announcement banner live (dismiss after 3 sessions)
- [ ] Product Hunt listing live at 12:01am PT (Jordan owns)
- [ ] Social posts scheduled: Twitter/LinkedIn (Jordan), Dev community (Sarah)

---

## Readiness Checklist

### Product & Engineering
- [x] Feature complete and passing QA (May 9)
- [x] Performance verified: p99 latency 187ms with 50 concurrent editors
- [x] Feature flag tested: on → off → on with no data loss
- [x] Sentry alert configured: error rate >1% pages on-call immediately
- [ ] Rollback runbook reviewed by Sarah (due May 25)
- [ ] Load test with 200 concurrent editors scheduled May 27

### Marketing (Jordan)
- [x] Blog post first draft complete — review by Alex by May 22
- [ ] Blog post final approved by May 26
- [ ] Email copy approved (send: May 30, 10am PT)
- [ ] Social posts drafted and scheduled (Twitter + LinkedIn, May 30)
- [ ] Product Hunt listing copy + assets ready (May 28)
- [ ] Screenshots: 3 polished screenshots + 1 GIF showing cursors (due May 24)

### Sales & CS (Jamie)
- [x] Sales brief sent to all AEs (May 10): feature summary, competitive positioning vs. Google Docs, pricing unchanged
- [ ] CS team training session (May 27, 30 min) — Jamie to run
- [ ] FAQ doc for CS ready in Notion by May 26
- [ ] Known issues doc ready: Firefox modal bug + workaround

### Documentation (Taylor)
- [x] Help center article drafted (pending final screenshots)
- [ ] Help article published by May 28
- [ ] In-app tooltip added to collab icon ("Click to invite teammates")
- [ ] RELEASE-004 release notes final draft reviewed by Alex (May 26)
- [ ] API docs updated: new `collaboration_session_id` field documented

---

## Timeline

| Date | Milestone | Owner | Status |
|------|-----------|-------|--------|
| May 9 | Feature complete + internal dog-food | Engineering | ✅ Done |
| May 10 | Sales brief sent to AEs | PM | ✅ Done |
| May 15 | 15 beta partners invited | PM | ✅ Done |
| May 16 | Beta live | Engineering | ✅ Done |
| May 21 | Beta feedback survey closes | PM | 🟡 Open |
| May 22 | Blog post review | PM + Marketing | 📋 Planned |
| May 24 | Screenshots + GIF assets ready | Marketing | 📋 Planned |
| May 26 | All copy approved (blog, email, release notes) | PM | 📋 Planned |
| May 27 | CS training session | CS | 📋 Planned |
| May 27 | Load test (200 concurrent editors) | Engineering | 📋 Planned |
| May 28 | Help article + API docs published | Docs | 📋 Planned |
| May 30 9am | Blog post live | Marketing | 📋 Planned |
| May 30 10am | Email to full user base | Marketing | 📋 Planned |
| May 30 12pm | Feature flag: GA for all Pro + Teams | Engineering | 📋 Planned |
| Jun 13 | 2-week post-launch review meeting | PM | 📋 Planned |

---

## Success Metrics

| Metric | Target | Baseline | Measurement | Review date |
|--------|--------|----------|-------------|-------------|
| Adoption: % of DAU using real-time collab | >20% in 30d | 0% | Product analytics | Jun 30 |
| Activation: complete a collab session with ≥2 users | >50% of adopters | — | Funnel analysis | Jun 30 |
| Free → Teams conversion rate | +3pp vs. May baseline (8% → 11%) | 8% | Billing data | Jun 30 |
| CSAT on collab feature | >4.2/5.0 | — | In-app survey, 7d post-use | Jun 30 |
| Support tickets: collab-related | <5/week | — | Zendesk tag `collab-v2.3` | Weekly |
| Error rate on collab sessions | <0.5% | — | Sentry | Daily |

---

## Risks & Rollback

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Error spike at GA (WebSocket capacity) | Medium | High | Load test May 27; scale WebSocket servers May 29 |
| Firefox modal bug causes visible UX issue | High | Low | CS FAQ ready; v2.3.1 fix ships May 27 |
| Low adoption (<10% in 30d) | Low | High | In-app prompt at day 7 if user hasn't tried; targeted email to active editors |
| Negative social reaction | Very low | Medium | CS response drafted; Alex on Slack watch during launch day |

**Rollback trigger:** If error rate >1% sustained for 5 consecutive minutes after GA flip:
1. Engineering disables feature flag (< 2 min to execute)
2. PM posts status update on status page
3. CS sends proactive email to affected users: "We've temporarily paused real-time editing while we fix an issue"
4. Engineering pages Sarah; root cause analysis within 1 hour

---

## Post-Launch: 2-Week Review Agenda (Jun 13)

1. Metric review: adoption, activation, conversion, CSAT, error rate
2. Top 5 CS tickets — any patterns?
3. Beta feedback themes — what did we get right / wrong?
4. v2.3.1 ship: Firefox fix + presence-on-disconnect
5. v2.4.0 scope: comments and annotations (PRD-010) — go or no-go?

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [PRD-007 Real-Time Collab Requirements](PRD-007-REALTIME_COLLAB.md) | Full feature requirements |
| [RELEASE-004 v2.3.0 Release Notes](RELEASE-004-v2_3_0.md) | Customer-facing release notes |
| [PERSONA-001 Startup PM](PERSONA-001-STARTUP_PM.md) | Primary target user for messaging |
| [RESEARCH-001 Competitive Analysis](RESEARCH-001-COMPETITIVE_ANALYSIS.md) | Market context (positioning vs. Google Docs) |
| [SPEC-015 Real-Time Collab Architecture](../SPEC-015-REALTIME_COLLAB.md) | Technical design reference |
