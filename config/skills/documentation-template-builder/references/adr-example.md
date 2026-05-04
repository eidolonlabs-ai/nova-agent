# Rich Example: Architecture Decision Record (ADR)

> Illustrative ADR in ai-companions style using the PostgreSQL vs Neo4j decision. Adapt for your architectural choices.

---

# ADR-010: Simplified Stack Architecture

**Status:** Accepted  
**Last Updated:** Mar 10, 2026  
**Type:** ADR (Architecture Decision)  
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
3. **Performance sufficient.** Embedding search is 50ms–500ms; acceptable for our use cases.
4. **Schema evolution.** Alembic migrations are well-understood, easy to test locally.

For the 5–10% of queries that need deep traversals, we'll use multi-table JOINs with strategic indexing. Benchmarks show this is still <200ms per query.

## Consequences

**Good:**
- ✅ Single database reduces ops burden
- ✅ 40% cheaper than Neo4j on Fly.io
- ✅ Faster deployments (schema changes are instant)
- ✅ Better local dev experience (Docker Compose is simpler)
- ✅ Native support for embeddings via pgvector

**Bad:**
- ⚠️ Graph traversals use JOINs (less intuitive than Cypher)
- ⚠️ No native graph query language (requires SQL)
- ⚠️ Need indexes for performance (requires understanding query patterns)

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
| Schema migration | 😞 Difficult | ✅ Easy | ⚠️ Tricky |

## Implementation Timeline

- ✅ **Mar 1:** Decision made
- ✅ **Mar 5–12:** Schema design (7 tables + indices)
- ✅ **Mar 13–20:** Data migration (Neo4j → PostgreSQL)
- ✅ **Mar 21:** Testing & validation
- ✅ **Mar 25:** Deploy to production

## Related Documentation

| Document | Purpose |
|----------|---------|
| [ADR-016](ADR-016-PG_KNOWLEDGE_GRAPH.md) | Schema design (depends on this ADR) |
| [ADR-002](ADR-002-AGENTIC_ARCHITECTURE.md) | Agent memory model (uses this architecture) |
| [SPEC-017](../spec/SPEC-017-LLM_ROBUSTNESS.md) | Retry logic for DB queries |
