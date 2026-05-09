# PRD-008: Real-Time Collaboration

**Status:** ✅ Approved  
**Last Updated:** May 2026  
**Type:** PRD (Product Requirements)  
**Author:** Alex Chen, Product Manager  
**Stakeholders:** Engineering Lead (Sarah), Design Lead (Mike), Customer Success (Jamie)

---

## Overview

**Problem:** Teams using our document platform lose work when multiple people edit simultaneously. Our current conflict resolution shows a "last writer wins" error, frustrating users and breaking workflows.

**Solution:** Implement real-time collaborative editing with live cursors, presence indicators, and operational transformation for conflict resolution. Users see changes as teammates type, with clear visual indication of who's editing what.

**Impact:** 
- Reduces support tickets by ~15% (currently 8 tickets/month on edit conflicts)
- Expected 25% increase in daily active users collaborating on documents
- Competitive parity with Google Docs and Notion
- Enables $50/month "Teams" tier launch (projected $200K ARR from 50 customers)

---

## Target Users

| User Type | Need | Priority |
|-----------|------|----------|
| Small teams (2–5 people) | Real-time co-editing without losing work | P0 |
| Enterprise users | Compliance audit trail + admin controls for collaboration | P1 |
| Power users | Advanced conflict resolution UI, version history | P1 |
| API integrations | WebSocket support for third-party tools | P2 |

---

## User Stories & Acceptance Criteria

### Story 1: Real-time collaborative editing
**As a** team member, **I want to** see my teammates' edits in real-time **so that** we can collaborate efficiently without losing work.

**Acceptance Criteria:**
- [ ] Document updates appear <200ms after teammate types
- [ ] Typing indicator shows "Sarah is editing line 3"
- [ ] Cursor position synced with <500ms latency
- [ ] Works in Chrome, Firefox, Safari (desktop + iPad)
- [ ] No data loss during edit conflicts
- [ ] Undo/redo respects all contributors' actions

**Notes:** 
- Use operational transformation (OT) for conflict resolution, not CRDT (simpler backend)
- Store all changes in `document_edits` table with user + timestamp
- Test with 50+ simultaneous editors to verify performance

### Story 2: Live presence indicators
**As a** document editor, **I want to** see who is currently editing **so that** I understand the document's edit state and can avoid stepping on teammates' toes.

**Acceptance Criteria:**
- [ ] Active editor list in top-right corner (avatar + name)
- [ ] Inactive users removed from list after 30s no activity
- [ ] Color-coded cursors show each user's edit position
- [ ] Hover over avatar shows "Sarah edited line 5, 2 minutes ago"
- [ ] Graceful disconnection handling (show as "offline")

**Notes:** 
- Use WebSocket for presence heartbeat every 5s
- Fall back to polling if WebSocket unavailable

### Story 3: Conflict resolution UI
**As a** power user, **I want to** see conflicts clearly resolved **so that** I trust the document integrity.

**Acceptance Criteria:**
- [ ] On conflict, show "Merge preview" with both versions
- [ ] User can select which version to keep (or manually merge)
- [ ] Original contributor gets notification of merge decision
- [ ] Change log shows all conflicts resolved
- [ ] Undo can revert a merge decision

---

## Success Metrics

| Metric | Target | Owner | Measurement | Timeline |
|--------|--------|-------|-------------|----------|
| Real-time edit latency | <200ms p99 | Engineering | APM dashboard | 30d post-launch |
| User adoption | >40% of documents edited collaboratively | Product | Analytics | 90d |
| Support tickets (conflicts) | <2/month (down from 8) | CS | Ticket tracking | 60d |
| Adoption by team size | 50% of 2+ person teams | Product | Cohort analysis | 90d |
| Churn impact | +5% retention for Teams tier | Product | Retention metrics | 120d |

---

## Constraints & Assumptions

**Constraints:**
- Must work with existing document schema (backward compatible)
- No breaking changes to public API
- Budget: 6 weeks of 2 engineers + 1 design lead
- Database: PostgreSQL (no new infrastructure)
- Max 100 concurrent editors per document (business rule, not technical)

**Assumptions:**
- Typical document size <10MB
- 95% of edit sessions <1 hour duration
- Network latency <100ms for 90% of users (US-based first)
- WebSocket support available in all target browsers

---

## Out of Scope

- [ ] Version history UI (separate PRD-009)
- [ ] Comments/annotations (separate PRD-010)
- [ ] Mobile app support (phase 2, separate work)
- [ ] Internationalization (global launch, phase 2)
- [ ] Advanced permissions (guest editing, read-only regions)

---

## Technical Constraints (from SPEC-015)

- Max message size: 64KB
- Operational transform library: automerge or yjs (TBD in SPEC)
- Must support offline mode (queues edits, syncs on reconnect)
- Database connections pooled at 20 max per node

---

## Timeline & Milestones

| Phase | Dates | Owner | Deliverable | Gate |
|-------|-------|-------|-------------|------|
| **Design** | May 15–22 | Mike (Design) | Figma mockups, interaction spec | Design review (Sarah) |
| **Backend** | May 23–Jun 10 | Engineering | OT engine, API, tests (80% coverage) | Code review + load test |
| **Frontend** | May 30–Jun 10 | Engineering | React component, WebSocket layer | Code review |
| **QA & Polish** | Jun 11–19 | QA | Testing, bug fixes, performance tune | <200ms latency verified |
| **Beta Launch** | Jun 20 | Product | Limited rollout to 10 customers | Feedback review |
| **Full Launch** | Jun 27 | Product | General availability, blog post | Success metrics baseline |

---

## Dependencies

- [ ] SPEC-015: Real-time collaboration technical design (due May 22)
- [ ] Database migration to add `document_edits` table (May 23)
- [ ] WebSocket infrastructure setup (May 20)
- [ ] Design mockups from Mike (May 22)

---

## Success Criteria (Post-Launch)

- ✅ 90%+ uptime for real-time collaboration
- ✅ <200ms edit latency p99
- ✅ Zero reported data loss from conflicts
- ✅ >30% of documents using real-time editing within 60d
- ✅ <2 support tickets/month on edit conflicts
- ✅ Team tier conversion rate >15%

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| WebSocket scaling issues | Medium | High | Load test with 200 concurrent users; fallback to polling |
| Data corruption from OT bugs | Low | Critical | 100% test coverage for merge logic; audit trail enabled |
| Performance regression | Medium | Medium | Benchmark against baseline; feature flag for rollout |
| User confusion on conflicts | Medium | Medium | Clear UI, in-app tutorial, support docs |

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [SPEC-015: Real-time Collaboration](../SPEC-015-REALTIME_COLLAB.md) | Technical architecture and API design |
| [Design Mockups](https://figma.com/...) | Figma prototype with interaction flows |
| [Market Research](https://docs.google.com/...) | Competitive analysis (Notion, Google Docs, Figma) |
| [Customer Feedback](https://sheets.google.com/...) | User interviews (15 customers, 3 themes) |
