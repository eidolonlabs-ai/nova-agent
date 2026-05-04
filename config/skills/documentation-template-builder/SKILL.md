---
name: documentation-template-builder
category: development
description: Create structured project documentation in ai-companions style with status indicators, quick references, link tables, and cross-references. Use this skill whenever a user asks to create, write, or generate project documentation, READMEs, roadmaps, specifications, deployment guides, architecture decisions, or operational guides. Generates complete markdown with suggested content, not just templates.
---

# Documentation Template Builder

Generate professional project documentation that matches the ai-companions style: clear hierarchy, status symbols, quick reference tables, cross-referenced structure, and comprehensive examples.

## Core Documentation Principles

### Structure & Hierarchy
- Use clear header hierarchy: `# Title` → `## Section` → `### Subsection` → `#### Detail`
- Start every doc with metadata: **Last Updated**, **Status**, and a brief purpose statement
- Include a "Start Here" or "Quick Reference" section at the top for busy readers
- Group related content in tables for scannability

### Status Symbols
Use these consistently throughout:
- `✅` — Complete, active, production-ready
- `🔴` — Blocked, critical issue, deprecated
- `🟡` — In progress, partial, needs review
- `📋` — Planned, roadmap item, pending
- `✏️` — Draft, being written
- `⚠️` — Warning, deprecated but still used
- `🔗` — Reference link, related doc

### Quick References & Tables
Every doc should include at least one of:
- **Quick reference table** — Shows status, purpose, and links in a grid
- **Quick steps section** — Copy-pasteable commands or step-by-step workflow
- **Summary table** — Counts, status breakdowns, completion percentages

### Cross-referencing
- Always include "Related Documentation" sections with links
- Use descriptive link text: `[Feature Spec](docs/SPEC-001.md)` not `[here](docs/SPEC-001.md)`
- Reference spec IDs, ADR numbers, doc type abbreviations (SPEC, ADR, RUN, GUIDE)
- Format: `[SPEC-XXX](path/SPEC-XXX.md) — Brief description`

---

## Documentation Types & Templates

### 1. README (Project Overview)

**Purpose:** First thing people read. Balance welcoming with informative.

**Structure:**
- Project name + tagline
- **Status at a glance** (1-2 lines with emoji)
- **Quick start** (5 min to understand + try)
- **What it does** (2-3 sentences, no jargon)
- **Key features** (bullet list with icons)
- **Getting started** (setup + first command)
- **Documentation index** (links to specs, guides, architecture)
- **Contributing** (link to CONTRIBUTING.md)

**Minimal Template:**
```markdown
# Project Name

**Status:** ✅ Active in production  
**Latest Release:** v2.1.0 (May 2026)

> Brief one-sentence description of what this project does.

## Quick Start

```bash
git clone <url>
cd <dir>
# Setup command
make install

# First command
make dev
```

See [Getting Started Guide](docs/GETTING_STARTED.md) for details.

## Features

- ✅ Feature one with benefit
- ✅ Feature two with benefit
- 📋 Planned feature coming soon

## Documentation

| Doc | Purpose |
|-----|---------|
| [Setup Guide](docs/SETUP.md) | Installation and configuration |
| [Architecture](docs/ARCHITECTURE.md) | System design overview |
| [Contributing](CONTRIBUTING.md) | How to contribute |

## License

MIT
```

**Rich Example:**
```markdown
# Nova Agent — Minimalist Personal AI

**Status:** ✅ Production ready  
**Latest Release:** v0.1.0  
**Type:** Single-user local agent with explicit token budgets

> Nova is a personal AI agent that runs locally with full control over model selection, API keys, and execution. Designed for developers who want an agentic experience without cloud lock-in.

## Why Nova?

- **Explicit budgets** — Token budgets at every layer (system, skills, tool results)
- **Model agnostic** — OpenRouter-compatible; switch models in config
- **Local first** — No cloud lock-in; your data stays on your machine
- **Skill-based** — Extend with markdown skill files, not code
- **Fast iteration** — 596 passing tests, type-safe Python

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/eidolonlabs-ai/nova-agent.git
cd nova-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Configure
cp config.yaml.example config.yaml
# Edit config.yaml with your OpenRouter API key

# 3. Chat
nova chat
```

## Features

| Feature | Status | Details |
|---------|--------|---------|
| Chat loop | ✅ Active | Streaming responses with history truncation |
| Tool calling | ✅ Active | 10+ built-in tools (terminal, file ops, search, web) |
| Skills system | ✅ Active | Extend with markdown in `~/.nova/skills/` |
| Memory | ✅ Active | File-based LRU store with search |
| Cost tracking | 📋 Planned | Per-conversation token budgets |

## Documentation

| Document | Type | Purpose |
|----------|------|---------|
| [Setup Guide](docs/SETUP.md) | GUIDE | Installation, configuration, first run |
| [Architecture](ARCHITECTURE.md) | ADR | System design, token budgets, memory |
| [Creating Skills](docs/GUIDE-002-CREATING_SKILLS.md) | GUIDE | Extend with custom knowledge domains |
| [Creating Tools](docs/GUIDE-001-CREATING_TOOLS.md) | GUIDE | Add new tool implementations |
| [API Reference](docs/API.md) | SPEC | Complete agent API and tool schemas |

## Tests & Quality

- **Test suite:** 596 tests, 75.69% coverage, all passing ✅
- **Type checking:** mypy clean (0 errors in 36 modules)
- **Linting:** ruff compliant
- **CI/CD:** GitHub Actions on every push

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines, code style, and the contribution workflow.

## License

MIT License. See LICENSE file for details.

## Support

- **Issues:** [GitHub Issues](https://github.com/eidolonlabs-ai/nova-agent/issues)
- **Discussions:** [GitHub Discussions](https://github.com/eidolonlabs-ai/nova-agent/discussions)
- **Docs:** [Full Documentation](docs/)
```

---

### 2. Roadmap (Phases & Timeline)

**Purpose:** Show project direction, completed work, and what's next.

**Structure:**
- Updated date and current phase status
- Phases with completion percentages
- Per-phase breakdown (what's done ✅, in progress 🟡, planned 📋, blocked 🔴)
- Timeline/sequencing
- Related specs
- Summary table with counts

**Minimal Template:**
```markdown
# Project Roadmap

**Updated:** May 2026  
**Current Phase:** Phase 2 (User Experience)  
**Overall Progress:** 65% complete (13/20 features)

---

## Phase 1: Core Features ✅ Completed

- ✅ Feature A
- ✅ Feature B
- ✅ Feature C

## Phase 2: User Experience 🟡 In Progress

- ✅ Subfeature 1 (complete)
- 🟡 Subfeature 2 (in progress, 50%)
- 📋 Subfeature 3 (planned)

## Phase 3: Scaling & Performance 📋 Planned

- 📋 Performance optimization
- 📋 Distributed deployment
- 📋 Analytics dashboard

---

## Timeline

| Phase | Target | Status |
|-------|--------|--------|
| Phase 1 | Jan 2026 | ✅ Complete |
| Phase 2 | Jun 2026 | 🟡 70% |
| Phase 3 | Dec 2026 | 📋 Planned |

## Next Steps

Immediate focus: Complete Phase 2 by June 30.
```

**Rich Example:**
```markdown
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
```

---

### 3. Specification (Feature Design)

**Purpose:** Detailed design of a single feature, system, or component.

**Structure:**
- Title + spec ID (SPEC-NNN)
- **Status** and last updated
- **Problem statement** — What problem does this solve?
- **Proposed solution** — High-level approach
- **Architecture** — System diagram or technical details
- **Data model** — Tables, schemas, key relationships
- **API/Interface** — How other systems interact with this
- **Examples** — Concrete usage scenarios
- **Trade-offs** — What we chose and why
- **Related specs** — Dependencies and cross-references

**Minimal Template:**
```markdown
# SPEC-NNN: Feature Name

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Author:** Name

---

## Problem

Describe the problem this feature solves in 2-3 sentences.

## Solution

High-level approach to solving the problem.

## Architecture

```
[ASCII diagram or description of component architecture]
```

## Data Model

```sql
CREATE TABLE feature (
  id UUID PRIMARY KEY,
  created_at TIMESTAMP,
  status TEXT
);
```

## API

```python
def create_feature(name: str, config: dict) -> Feature:
    """Create a new feature with the given config."""
```

## Examples

### Example 1: Basic usage
```python
feature = create_feature("example", {"enabled": True})
```

## Trade-offs

- Choice A vs Choice B: We chose A because...

## Related Specs

- [SPEC-NNN](SPEC-NNN.md) — Related feature
```

**Rich Example:**
```markdown
# SPEC-018: Reflective Agent Improvements (Socially Aware Agent)

**Status:** ✅ Complete  
**Last Updated:** Apr 23, 2026  
**Author:** Engineering Team  
**Related Specs:** [SPEC-015](SPEC-015-AGENTIC_WORKFLOW.md), [SPEC-073](SPEC-073-SHARED_LORE_ARCHITECTURE.md)

---

## Problem

The agent responds with generic empathy without genuine understanding of character relationships, emotional context, or social dynamics. Responses lack warmth and personalization, leading to lower user engagement.

**Current gap:** Agent sees user input as isolated queries, not social interactions.

## Proposed Solution

Implement a three-layer social awareness system:
1. **Relationship tracking** — Monitor trust, conflict history, shared experiences
2. **Emotional context** — Detect mood, stress, relationship changes from conversation
3. **Associative search** — Retrieve relevant relationship memories before responding

## Architecture

```
User Message
    ↓
[Emotional Detection] — Extract mood, context, stakes
    ↓
[Relationship Lookup] — Find relevant memories (friend/enemy/stranger)
    ↓
[Reflective Agent] — Generate response with social context
    ↓
Response (Warm, personalized, emotionally intelligent)
```

### Emotional Detection (Layer 1)
- Analyze for: stress signals, relationship mentions, conflict markers, celebration indicators
- Store signals in user context (temporary session state)
- Merge with relationship history for full context

### Relationship Tracking (Layer 2)
Database schema:
```sql
CREATE TABLE relationships (
  id UUID PRIMARY KEY,
  character_id UUID,
  user_id UUID,
  trust_level INT (1-100),
  interaction_count INT,
  last_conflict TIMESTAMP,
  shared_experiences TEXT[],
  updated_at TIMESTAMP
);
```

### Associative Search (Layer 3)
Before generating response:
1. Query shared_experiences for emotionally relevant memories
2. Rank by recency and relevance
3. Include 2-3 most relevant memories in context
4. Agent uses these to personalize response

## Examples

### Example 1: Friend detecting stress
```
User: "I've had such a rough week. Work is killing me."
Agent recognizes: stress signal, time context
Looks up: relationship_type=friend, last_interaction=3_days_ago, shared_experiences=[work_complaints]
Response: "Hey, I noticed you've been stressed lately. Remember when you said you'd take that vacation? Maybe it's time?"
```

### Example 2: New character building rapport
```
User: "Tell me about yourself."
Agent recognizes: first-time interaction, trust_level=new
Looks up: No prior experiences, focus on introduction
Response: "I'm here to get to know you better. I'm curious about what matters to you..."
```

## Implementation Checklist

- ✅ Emotional detection module
- ✅ Relationship database schema
- ✅ Associative search ranking
- ✅ Integration with agent prompt
- 🟡 Testing on production conversations (in progress)

## Trade-offs

| Decision | Alternative | Why We Chose This |
|----------|-------------|-------------------|
| PostgreSQL for relationships | Redis cache | Permanent history needed for personality evolution |
| In-prompt memories | Separate retrieval system | Faster latency, simpler architecture |
| 3-layer system | Single embedding similarity | More nuanced understanding of social context |

## Performance

- Relationship lookup: <50ms (indexed query)
- Emotional detection: <100ms (regex + ML)
- Total latency addition: <200ms per response

## Related Specs

- [SPEC-015](SPEC-015-AGENTIC_WORKFLOW.md) — Base agent architecture
- [SPEC-073](SPEC-073-SHARED_LORE_ARCHITECTURE.md) — Long-term memory structure
- [ADR-010](../adr/ADR-010-SIMPLIFIED_STACK_ARCHITECTURE.md) — Database design
```

---

### 4. Deployment Guide (RUN docs)

**Purpose:** Step-by-step instructions for deploying/running the system.

**Structure:**
- **Prerequisites** checklist
- **Quick steps** for experienced users
- **Detailed walkthrough** with explanations
- **Verification steps** to confirm it worked
- **Troubleshooting** common issues
- **Related docs** (architecture, specs, rollback)

**Minimal Template:**
```markdown
# Deployment Guide

**Last Updated:** May 2026  
**Type:** RUN (Operational Procedure)

---

## Prerequisites

- [ ] Administrator access
- [ ] Config file (`config.yaml`)
- [ ] Database backups completed
- [ ] Notify team 24 hours before

## Quick Steps (5 min)

```bash
./deploy-script.sh
# Verify with: make verify
```

## Detailed Steps

### 1. Pre-deployment
```bash
# Backup database
pg_dump production > backup_$(date +%s).sql

# Review changes
git log main...production
```

### 2. Deploy
```bash
git checkout production
git pull origin production
./scripts/deploy.sh
```

### 3. Verify
```bash
curl https://api.example.com/health
# Should return {"status":"ok"}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Deploy fails | Check logs: `tail -f /var/log/deploy.log` |
| Health check fails | Run `./scripts/rollback.sh` |

## Rollback

```bash
./scripts/rollback.sh <timestamp>
```

## Related Docs

- [Architecture](ARCHITECTURE.md)
- [Database Migrations](MIGRATIONS.md)
```

**Rich Example:**
```markdown
# Deployment Guide: Backend to Production (Fly.io)

**Last Updated:** May 2026  
**Type:** RUN (Operational Procedure)  
**Audience:** DevOps, Release Manager  
**Related:** [ADR-012](../adr/ADR-012-CLOUD_DEPLOYMENT_STORAGE.md), [Database Migrations](SPEC-060-DATABASE_MIGRATIONS.md)

---

## Prerequisites Checklist

- [ ] All tests passing locally (`pytest`)
- [ ] Code reviewed and approved
- [ ] Database backup scheduled
- [ ] Slack notifications enabled
- [ ] Rollback plan confirmed
- [ ] Team notified (if breaking changes)

## Quick Steps (Experienced)

```bash
# 1. Ensure clean state
git status
git pull origin main
poetry install

# 2. Run tests
pytest

# 3. Deploy
fly deploy -a ai-companions-prod

# 4. Migrate if needed
fly ssh console -a ai-companions-prod -C "alembic upgrade head"

# 5. Verify
curl https://api.ai-companions.com/health
```

## Detailed Walkthrough

### Phase 1: Pre-Deployment (30 min before)

**1.1 Verify test suite**
```bash
cd backend
poetry install
pytest -v --cov=app
# All tests must pass
```

**1.2 Check Fly.io status**
```bash
fly status -a ai-companions-prod
# Should show: "Running"
```

**1.3 Announce in Slack**
```
@team Deploying backend to production in 10 minutes.
Changes: [link to PR or commit]
```

### Phase 2: Database Migrations (if needed)

**2.1 Create migration**
```bash
cd backend
alembic revision --autogenerate -m "Describe change"
# Review generated file in alembic/versions/
```

**2.2 Test migration locally**
```bash
docker-compose up -d
docker exec -it ai-companions-backend-1 alembic upgrade head
docker exec -it ai-companions-backend-1 alembic current
# Verify state looks correct
```

**2.3 Commit migration**
```bash
git add backend/alembic/versions/
git commit -m "add migration: describe change"
git push origin feature-branch
```

### Phase 3: Deploy Backend

**3.1 Build and deploy**
```bash
fly deploy -a ai-companions-prod --remote-only
# Takes ~5 min
# Watch output for: "App deployed successfully"
```

**3.2 Run migrations**
```bash
fly ssh console -a ai-companions-prod
alembic upgrade head
alembic current
# Output should show migration head with (head) marker
exit
```

**3.3 Verify deployment**
```bash
# Health check
curl -s https://api.ai-companions.com/health | jq .

# Sample API call
curl -s https://api.ai-companions.com/chats | jq '.[] | .id' | head -5
```

### Phase 4: Verification & Monitoring (10 min)

**4.1 Check logs**
```bash
fly logs -a ai-companions-prod --lines 50
# Should show: No ERROR lines in last 50 logs
```

**4.2 Monitor metrics**
- CPU: Should stay <70% ([Grafana](https://grafana.internal/d/backend-prod))
- Memory: Should stay <80%
- Errors: Should be 0–2 per minute (not 50+)

**4.3 Announce success**
```
✅ Backend deployed to production.
Version: [commit hash]
Changes: [link to PR]
```

## Rollback Procedure

If something breaks:

```bash
# 1. Immediate rollback
fly cancel-deployment -a ai-companions-prod
# OR
fly deploy -a ai-companions-prod --image <previous-image-hash>

# 2. If database migration broke, rollback migration
fly ssh console -a ai-companions-prod -C "alembic downgrade -1"

# 3. Verify
curl https://api.ai-companions.com/health

# 4. Announce
@team Rolled back deployment. Investigating issue.
```

## Troubleshooting

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| Deploy hangs | Check Fly.io status with `fly status` | Cancel and retry: `fly cancel-deployment` |
| Health check fails | Check logs: `fly logs -a ai-companions-prod` | Likely migration issue; rollback with `alembic downgrade -1` |
| High error rate | Check Sentry alerts | Rollback deployment; open incident |
| Database timeout | Run `alembic current` to check migration state | Manually fix state or rollback |

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Database Migrations](SPEC-060-DATABASE_MIGRATIONS.md) | How migrations work, troubleshooting |
| [ADR-012](../adr/ADR-012-CLOUD_DEPLOYMENT_STORAGE.md) | Deployment architecture decisions |
| [Frontend Deployment](FRONTEND_FLY_DEPLOYMENT.md) | Web UI deployment steps |
| [CI/CD Setup](CICD_SETUP.md) | GitHub Actions configuration |

## Post-Deployment (Optional)

- [ ] Run smoke tests against production
- [ ] Monitor Grafana dashboard for 1 hour
- [ ] Notify customer success of new features
```

---

### 5. Architecture Decision Record (ADR)

**Purpose:** Document important architectural decisions and their rationale.

**Structure:**
- **Status** — Proposed, Accepted, Deprecated
- **Problem** — What decision needed to be made?
- **Options considered** — At least 2 alternatives
- **Decision** — What we chose and why
- **Consequences** — Trade-offs and implications
- **Related decisions** — Dependencies on other ADRs

**Minimal Template:**
```markdown
# ADR-NNN: Decision Title

**Status:** Accepted  
**Last Updated:** May 2026  
**Author:** Name

---

## Problem

Why did we need to make this decision?

## Options Considered

### Option 1: First approach
Pros: ...
Cons: ...

### Option 2: Second approach
Pros: ...
Cons: ...

## Decision

We chose Option 1 because ...

## Consequences

**Good:**
- Benefit 1
- Benefit 2

**Bad:**
- Trade-off 1
- Trade-off 2

## Related ADRs

- [ADR-NNN](ADR-NNN.md) — Related decision
```

**Rich Example:**
```markdown
# ADR-010: Simplified Stack Architecture

**Status:** Accepted  
**Last Updated:** Mar 10, 2026  
**Author:** Engineering Team  
**Supersedes:** ADR-005 (Neo4j Knowledge Graph)

---

## Problem

Our knowledge graph used Neo4j, which introduced operational complexity:
- Separate database to manage and back up
- Limited Fly.io support for graph databases
- High memory usage on small deployments
- Difficult schema migrations

Yet we need:
- Efficient semantic search (embeddings)
- Relationship tracking (who knows whom, conversation history)
- Scalability to millions of knowledge items

Can we simplify the stack while maintaining these capabilities?

## Options Considered

### Option 1: Keep Neo4j (Status Quo)
**Pros:**
- Graph queries are natural for relationships
- Rich query language (Cypher)

**Cons:**
- Operational burden (separate service)
- Not Fly.io native
- High memory footprint
- Schema evolution is painful

### Option 2: PostgreSQL with pgvector (Chosen)
**Pros:**
- Single database (simpler ops)
- Native Fly.io support
- Excellent performance for embeddings
- Easy schema migrations (Alembic)
- JSONB for flexible data

**Cons:**
- Relationship queries less elegant (SQL JOINs)
- Slightly slower for deep graph traversals (rare in our use case)

### Option 3: Hybrid (PostgreSQL + Redis)
**Pros:**
- Fast caching layer
- Separates hot/cold data

**Cons:**
- More services = more ops
- Cache invalidation complexity
- Not worth it for our scale

## Decision

**Adopt PostgreSQL + pgvector (Option 2).**

**Rationale:**
1. **Simplicity wins.** One database means faster deployments, fewer failure modes.
2. **Fly.io native.** PostgreSQL has first-class Fly.io support.
3. **Performance sufficient.** Embedding similarity search is 50ms–500ms depending on index; acceptable for our use cases.
4. **Schema evolution.** Alembic migrations are well-understood, easy to test locally.

For the 5–10% of queries that need deep traversals, we'll use multi-table JOINs with strategic indexing. Benchmarks show this is still <200ms per query.

## Consequences

**Good:**
✅ Single database reduces ops burden  
✅ 40% cheaper than Neo4j on Fly.io  
✅ Faster deployments (schema changes are instant)  
✅ Better local dev experience (Docker Compose is simpler)  
✅ Native support for embeddings via pgvector  

**Bad:**
⚠️ Graph traversals use JOINs (less intuitive than Cypher)  
⚠️ No native graph query language (requires SQL)  
⚠️ Need indexes for performance (requires understanding query patterns)  

**Mitigations:**
- Document common query patterns
- Pre-create indexes for known use cases
- Monitor slow queries via Fly.io Postgres console

## Comparison Table

| Aspect | Neo4j | PostgreSQL | Redis Hybrid |
|--------|-------|-----------|--------------|
| Ops simplicity | ❌ High | ✅ Simple | ⚠️ Medium |
| Fly.io support | ⚠️ Partial | ✅ Native | ⚠️ Partial |
| Cost | 💰 High | 💰 Low | 💰 Medium |
| Embedding search | ⚠️ Plugins | ✅ pgvector | ✅ Redis |
| Query language | Cypher | SQL | N/A |
| Schema migration | 😞 Difficult | ✅ Easy | ⚠️ Tricky |

## Implementation Timeline

- ✅ **Mar 1:** Decision made
- ✅ **Mar 5–12:** Schema design (7 tables + indices)
- ✅ **Mar 13–20:** Data migration (Neo4j → PostgreSQL)
- ✅ **Mar 21:** Testing & validation
- ✅ **Mar 25:** Deploy to production

## Related Decisions

- **[ADR-016](ADR-016-PG_KNOWLEDGE_GRAPH.md)** — Schema design (depends on this ADR)
- **[ADR-002](ADR-002-AGENTIC_ARCHITECTURE.md)** — Agent memory model (uses this architecture)
- **[SPEC-017](../spec/SPEC-017-LLM_ROBUSTNESS.md)** — Retry logic for DB queries
```

---

### 6. Operational Guide (Quick Reference)

**Purpose:** Day-to-day operational procedures and troubleshooting.

**Structure:**
- **Quick reference** for common tasks
- **Commands** that can be copy-pasted
- **Monitoring** — What to watch, alerts
- **Troubleshooting** — Common issues and fixes
- **Escalation** — When to page someone

**Minimal Template:**
```markdown
# Operational Guide

**Last Updated:** May 2026  
**On-call contact:** @oncall  
**Escalation:** [Slack channel]

---

## Quick Reference

| Task | Command |
|------|---------|
| Check health | `curl /health` |
| View logs | `tail -f /var/log/app.log` |
| Restart service | `systemctl restart app` |

## Common Tasks

### Task 1: Task name
```bash
step 1
step 2
step 3
```

## Monitoring & Alerts

- **CPU >80%:** Check `top` and kill heavy processes
- **Memory >90%:** Restart service
- **Errors >100/min:** Page oncall

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| Connection timeout | DB offline | Restart DB |
| 503 Service Unavailable | Out of memory | Increase RAM or restart |

## Escalation

If you can't fix it in 5 min: page @oncall
```

**Rich Example:**
```markdown
# Operational Guide: AI Companions Backend

**Last Updated:** May 3, 2026  
**Type:** GUIDE (Operational)  
**On-call contact:** @backend-oncall (Slack)  
**Escalation policy:** 5 min to fix, then page; >30 min page manager  
**Related:** [Deployment Guide](DEPLOY_TO_FLY.md), [Architecture](ADR-010-SIMPLIFIED_STACK_ARCHITECTURE.md)

---

## Quick Reference

| Task | Command | Time |
|------|---------|------|
| Check prod status | `fly status -a ai-companions-prod` | 10s |
| View live logs | `fly logs -a ai-companions-prod --lines 100` | 5s |
| Check database | `fly postgres connect -a ai-companions-prod` | 20s |
| Restart backend | `fly restart -a ai-companions-prod` | 2 min |
| Check metrics | [Grafana Dashboard](https://grafana.internal/d/backend-prod) | 30s |

## Common Tasks

### 1. Check service health

```bash
# Quick health check
curl -s https://api.ai-companions.com/health | jq .

# Expected response:
# {
#   "status": "ok",
#   "version": "v2.1.0",
#   "timestamp": "2026-05-03T14:30:00Z"
# }

# If not 200, proceed to troubleshooting
```

### 2. View error logs

```bash
# Last 50 lines
fly logs -a ai-companions-prod --lines 50

# Filter for errors
fly logs -a ai-companions-prod --lines 500 | grep ERROR

# Follow in real-time
fly logs -a ai-companions-prod
# (press Ctrl+C to exit)
```

### 3. Restart service (if hung)

```bash
fly restart -a ai-companions-prod
# Takes ~90 seconds

# Verify it came back up
sleep 120
curl https://api.ai-companions.com/health
```

### 4. Check database connectivity

```bash
fly ssh console -a ai-companions-prod
psql $DATABASE_URL -c "SELECT 1;"
# If returns "1", DB is responding
exit
```

### 5. Emergency: Scale down then up

For severe issues:

```bash
# Scale to 0 (kill all instances)
fly scale count 0 -a ai-companions-prod

# Wait 30s
sleep 30

# Scale back up
fly scale count 2 -a ai-companions-prod

# Verify health
sleep 60
curl https://api.ai-companions.com/health
```

## Monitoring & Alerts

### Key Metrics (Check Grafana)

| Metric | Normal | Alert | Action |
|--------|--------|-------|--------|
| CPU | <50% | >80% for 5 min | Check top process; restart if needed |
| Memory | <60% | >85% for 5 min | Increase RAM tier or restart |
| Request latency | <200ms | >500ms p95 | Check slow queries; page DB team |
| Error rate | <0.1% | >1% | Page oncall immediately |
| Database connections | <20 | >50 | Check for connection leaks; restart |

### Alert Escalation

1. **⚠️ Warning (10 min to respond)**
   - CPU 70–80%
   - Error rate 0.5–1%
   - → Check logs, diagnose

2. **🔴 Critical (immediate response)**
   - CPU >85%
   - Error rate >2%
   - Database offline
   - → Page oncall

3. **🟠 Degraded (reduce load)**
   - Latency spiking
   - Connection pool near limit
   - → Restart or scale up

## Troubleshooting

### Issue: "502 Bad Gateway"

**Diagnosis:**
```bash
fly status -a ai-companions-prod
curl https://api.ai-companions.com/health
fly logs -a ai-companions-prod --lines 50 | grep ERROR
```

**Possible causes:**
| Cause | Check | Fix |
|-------|-------|-----|
| Backend down | Is status showing "Running"? | `fly restart` |
| Database offline | Run `psql $DATABASE_URL -c "SELECT 1;"` | Page DB team |
| Out of memory | Check Grafana memory graph | `fly scale memory 2G` |

### Issue: "High error rate (>1% HTTP 500s)"

**Steps:**
```bash
# 1. View errors
fly logs -a ai-companions-prod --lines 500 | grep ERROR | head -20

# 2. Identify pattern (database, timeout, etc.)

# 3. If database issue
fly ssh console -a ai-companions-prod -C "psql $DATABASE_URL -c 'SELECT count(*) FROM pg_stat_activity;'"

# 4. If timeout issue, increase timeout in config:
# Edit config.yaml, increase query_timeout from 30s to 60s
# Redeploy: fly deploy -a ai-companions-prod
```

### Issue: "Database full / out of space"

**Check usage:**
```bash
fly ssh console -a ai-companions-prod
psql $DATABASE_URL -c "SELECT pg_size_pretty(pg_database_size(current_database()));"
# If >90% of disk, escalate to infrastructure team
exit
```

**Quick fix (archive old data):**
```bash
fly ssh console -a ai-companions-prod
# Connect to DB and run archival script
psql $DATABASE_URL < scripts/archive_old_conversations.sql
exit

# Verify space freed
fly ssh console -a ai-companions-prod -C "psql $DATABASE_URL -c 'SELECT pg_size_pretty(pg_database_size(current_database()));'"
```

### Issue: "Slow API responses (>500ms p95)"

**Diagnosis:**
```bash
# Check if database is slow
fly ssh console -a ai-companions-prod
psql $DATABASE_URL -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 5;"
```

**Fix options:**
1. **Add index:** `CREATE INDEX idx_name ON table (column);`
2. **Optimize query:** Refactor to avoid full table scan
3. **Increase timeout:** If queries are correct but slow
4. **Scale database:** Upgrade to bigger compute

## Escalation Tree

```
Issue detected
    ↓
Can you fix in <5 min? YES → Fix it, document in #incidents
    ↓ NO
Page @backend-oncall (Slack: @oncall)
    ↓
Oncall can't fix in 10 min?
    ↓
Page @backend-manager + incident commander
```

## On-Call Shift Handoff

When taking over oncall:

```bash
# 1. Check status
fly status -a ai-companions-prod

# 2. Review last 24h incidents
# Check #incidents Slack channel

# 3. Check metrics
# Open Grafana: https://grafana.internal/d/backend-prod

# 4. Run health check
curl https://api.ai-companions.com/health

# 5. Post in #incidents:
# "✅ @backend-oncall shift handoff complete. All systems nominal."
```

## Quick Links

- **Fly.io Dashboard:** https://fly.io/apps/ai-companions-prod
- **Grafana Metrics:** https://grafana.internal/d/backend-prod
- **Database Browser:** [pgAdmin](https://pgadmin.internal)
- **Slack:** #backend, #incidents, @backend-oncall
- **Related Docs:** [Deployment Guide](DEPLOY_TO_FLY.md), [Architecture](ADR-010-SIMPLIFIED_STACK_ARCHITECTURE.md)
```

---

## Best Practices Summary

### Always Include

- `**Last Updated:** MONTH YEAR` at the top
- Status indicator in first 100 words (✅/🔴/🟡/📋)
- A "quick reference" or "quick steps" section
- Links to related documentation
- Table for grouped information (specs, commands, metrics)

### Status Symbol Rules

Use consistently across your docs:
- ✅ **Active/Complete** — Production-ready, done
- 🔴 **Blocked/Deprecated** — Don't use, major issue
- 🟡 **In Progress/Partial** — Work in progress, partial support
- 📋 **Planned** — Roadmap item, not started
- ✏️ **Draft** — Early stage, not final
- ⚠️ **Caution** — Works but with caveats
- 🔗 **Reference** — Link to other docs

### Formatting Tips

**For links:** Always use descriptive text
```markdown
✅ [SPEC-015 Agentic Workflow](docs/spec/SPEC-015.md) — How agent reasoning works
❌ [Link](docs/spec/SPEC-015.md)
```

**For code blocks:** Use language hints
```markdown
# ✅ Good (language-specific highlighting)
```bash
fly deploy -a app-prod
```

# ❌ Bad (no syntax highlighting)
fly deploy -a app-prod
```

**For tables:** Keep them scannable
- Max 5 columns
- Use symbols instead of long text where possible
- Sort by status/importance, not alphabetically

---

## Usage Examples

### Generating a README
```
User: "Create a README for my new data pipeline project"
Skill: Generates rich README with features, quick start, architecture links
```

### Generating a Spec
```
User: "Write a specification for our new caching layer"
Skill: Creates SPEC with problem, solution, architecture, examples, trade-offs
```

### Generating a Roadmap
```
User: "Document our Q2–Q3 roadmap with status"
Skill: Creates phases table, shows completed/in-progress/planned items with symbols
```

### Generating Deployment Guide
```
User: "Write deployment steps for deploying to Kubernetes"
Skill: Creates quick steps, detailed walkthrough, verification, troubleshooting
```
