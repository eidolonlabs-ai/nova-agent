# RESEARCH-001: Competitive Analysis — Document Collaboration Tools

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** RESEARCH (Competitive Analysis)  
**Author:** Alex Chen, Product Manager  
**Next review:** August 2026 (quarterly)

---

## TL;DR

The document collaboration market is crowded at the top (Notion, Confluence, Google Docs) and fragmented at the bottom (dozens of niche tools). The big players win on breadth and integrations; they lose on opinionated structure and workflow intelligence. No competitor tells teams *how* to document — they just provide a blank canvas.

**Our positioning:** We win when a team wants consistent, professional documentation without spending hours on formatting or starting from scratch. We lose when a team needs a full wiki, database views, or deep Jira/Confluence integration.

---

## Competitors Overview

| Competitor | Segment | Pricing | Core strength | Key weakness |
|------------|---------|---------|---------------|--------------|
| Notion | SMB + prosumer | Free / $8–$15/seat/mo | Flexibility, databases, all-in-one | Overwhelming blank canvas; no opinionated structure |
| Confluence | Enterprise | $5.75–$10.50/seat/mo | Jira integration, permission controls | Slow, clunky UI; steep learning curve for non-eng |
| Google Docs | All | Free (Workspace: $6+/seat) | Real-time collab, familiar, fast | No structure, no templates ecosystem, no cross-linking |
| Coda | SMB + ops teams | Free / $10/seat/mo | Docs + spreadsheets combined | Niche use case; not PM-focused |
| Linear Docs | Dev teams | Bundled with Linear | Issue-linked docs, fast | Dev-only audience; no PM or strategy doc templates |
| **Us** | PM + product teams | $12/seat/mo (Teams) | Opinionated PM templates, cross-linked, quality feedback | Smaller integrations library; newer brand |

---

## Competitor Teardowns

### Notion

**Overview:** Notion is the most popular "all-in-one" workspace for SMB and prosumer users. It combines docs, databases, wikis, and project tracking into a single tool with extreme flexibility.

**Strengths:**
- ✅ Extreme flexibility — you can build almost any workflow
- ✅ Strong template gallery (community + official)
- ✅ Database views (table, kanban, calendar, gallery) that PMs love for roadmaps
- ✅ AI writing assistant now built-in (Notion AI, $10/seat add-on)
- ✅ 50+ native integrations (Slack, GitHub, Figma, Jira)

**Weaknesses:**
- 🔴 Blank canvas problem — new teams don't know where to start; template discovery is poor
- 🔴 No cross-document intelligence — docs exist in isolation; no "related docs" awareness
- 🔴 Template quality is inconsistent — community templates range from excellent to unusable
- 🔴 No guidance on *what makes a good PRD* — just a blank page with a header
- 🔴 Performance degrades noticeably with large databases (>10K rows)

**Pricing:** Free (limited blocks) / Plus $8/seat/mo / Business $15/seat/mo / Enterprise custom  
**Notable customers:** Figma, Pixar, Nike (marketing), many startups  
**Key battle vs. us:** Notion has the brand and distribution; we have opinionated structure and PM expertise. Customers choose us when they want docs that *teach* best practices, not just store content.

---

### Confluence

**Overview:** Confluence is Atlassian's enterprise wiki and documentation platform, deeply integrated with Jira. It dominates large engineering organizations.

**Strengths:**
- ✅ Deep Jira integration — link docs to tickets, epics, sprints natively
- ✅ Enterprise-grade permissions, SSO, audit logs
- ✅ Strong space/page hierarchy for large teams
- ✅ Broad Atlassian ecosystem (Jira, Bitbucket, Trello)

**Weaknesses:**
- 🔴 UI is dated and slow — users frequently cite it as "painful" in G2 reviews
- 🔴 High learning curve for non-engineering users (PMs, designers, marketers)
- 🔴 Template library is sparse and low quality outside engineering docs
- 🔴 Real-time collaboration is poor vs. Google Docs or Notion
- 🔴 Mobile experience is nearly unusable

**Pricing:** Free (10 users) / Standard $5.75/seat/mo / Premium $10.50/seat/mo / Enterprise custom  
**Notable customers:** Most Fortune 500 companies with Jira  
**Key battle vs. us:** Confluence wins on enterprise compliance and Jira lock-in. We win when a team wants docs that non-engineers actually use. Common pattern: teams use Confluence for engineering ADRs and switch to us for product docs.

---

### Google Docs

**Overview:** Google Docs is the default collaboration tool for teams already in Google Workspace. It wins on familiarity and real-time editing; it loses on structure.

**Strengths:**
- ✅ Best-in-class real-time collaboration (no latency, no conflicts)
- ✅ Free with Google Workspace; near-universal adoption
- ✅ Fast, reliable, works offline
- ✅ Excellent comment and suggestion UX

**Weaknesses:**
- 🔴 No structure whatsoever — a PRD looks identical to a meeting notes doc
- 🔴 No templates with intelligence — Google's template gallery is cosmetic only
- 🔴 No cross-referencing between docs
- 🔴 Search within Docs is weak (searching across many docs is painful)
- 🔴 No status indicators, no lifecycle management

**Pricing:** Free / Workspace $6–$18/user/mo  
**Key battle vs. us:** Google Docs is the incumbent we're always competing against. We win on structure, discoverability, and consistency. We lose when "free and familiar" is the only criterion.

---

## Feature Comparison Matrix

| Feature | Us | Notion | Confluence | Google Docs |
|---------|-----|--------|------------|-------------|
| PRD template | ✅ | 🟡 Community | 🟡 Basic | ❌ |
| Persona template | ✅ | ❌ | ❌ | ❌ |
| ADR template | ✅ | 🟡 Community | 🟡 Engineering-focused | ❌ |
| GTM plan template | ✅ | ❌ | ❌ | ❌ |
| Cross-doc linking with context | ✅ | 🟡 Manual | 🟡 Manual | ❌ |
| Real-time co-editing | ✅ v2.3.0 | ✅ | 🟡 Slow | ✅ Best-in-class |
| Status indicators (✅🟡📋) | ✅ | ❌ | ❌ | ❌ |
| AI writing assistance | 📋 H2 | ✅ Add-on | 🟡 Beta | ✅ Bundled |
| Jira / Linear integration | 📋 H2 | ✅ | ✅ Native | 🟡 Manual |
| Enterprise SSO + audit logs | 📋 H2 | ✅ | ✅ | ✅ |
| Mobile app | ❌ | ✅ | 🟡 Poor UX | ✅ |

Legend: ✅ Full support · 🟡 Partial / limited · ❌ Not available · 📋 Planned

---

## Positioning Gaps

**Where we are clearly ahead:**
- Opinionated PM template suite (PRD, PERSONA, STRATEGY, GTM) — no competitor has all of these
- Status lifecycle management (✅🟡📋) built into the format — competitors don't have this
- Cross-document intelligence (SPEC links to PRD which links to PERSONA) — unique

**Where we are at parity:**
- Real-time collaboration (shipped v2.3.0 — now table stakes)
- Basic doc editing and formatting

**Where we are behind (and it matters):**
- **AI writing assistant** — Notion and Google both have AI; customers are starting to ask; close with PRD-015 by Q3
- **Jira/Linear integration** — top enterprise ask; close with PRD-016 by Q4
- **Mobile app** — not blocking sales today, but will be in 12 months as team sizes grow

**Where we choose not to compete:**
- Database / spreadsheet views (Notion, Coda territory — not our user's primary need)
- Project management / ticketing (Linear, Jira territory — we integrate, not compete)

---

## Strategic Implications

| Insight | Action | Owner | Priority |
|---------|--------|-------|----------|
| Notion's blank canvas is our biggest opening — teams don't know how to start | Double down on template quality and discoverability; ship template gallery in-app | PM | P0 |
| AI writing is now expected — Notion AI has 800K subscribers | Accelerate AI draft-assist (PRD-015) to H2; can't wait until 2027 | PM | P0 |
| Confluence owns enterprise but users hate it — clear wedge opportunity | Build enterprise features (SSO, audit, Jira integration) for H1 2027 | PM | P1 |
| Google Docs users churn when they want structure — target with landing pages | "Structure for Google Docs users" SEO + migration guide | Marketing | P1 |

---

## Sources

- G2 reviews: Top 30 reviews per competitor, filtered May 2026
- Customer interviews: 12 interviews asked "what else do you use?" and "why did you switch?"
- Personal product testing: All four tools tested with a real PRD workflow (April 2026)
- Pricing pages: Verified May 8, 2026 — re-check quarterly (pricing changes frequently)
- Capterra comparison reports: Downloaded April 2026

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [STRATEGY-001 H2 2026](STRATEGY-001-H2_2026.md) | Strategic bets informed by this competitive landscape |
| [PRD-015 AI Writing Assist](PRD-015-AI_WRITING_ASSIST.md) | Closes the AI gap identified here |
| [PERSONA-001 Startup PM](PERSONA-001-STARTUP_PM.md) | Primary user for whom these trade-offs matter most |
