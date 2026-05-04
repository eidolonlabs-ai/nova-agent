# Rich Example: Specification (SPEC) Documentation

> Illustrative SPEC in ai-companions style. Adjust IDs, data models, and relationships for your feature.

---

# SPEC-018: Reflective Agent Improvements (Socially Aware Agent)

**Status:** ✅ Complete  
**Last Updated:** Apr 23, 2026  
**Type:** SPEC (Feature Specification)  
**Author:** Engineering Team  
**Related:** [SPEC-015](SPEC-015-AGENTIC_WORKFLOW.md), [SPEC-073](SPEC-073-SHARED_LORE_ARCHITECTURE.md)

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
  trust_level INT,         -- 1–100
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
3. Include 2–3 most relevant memories in context
4. Agent uses these to personalize response

## Examples

### Example 1: Friend detecting stress

```
User: "I've had such a rough week. Work is killing me."
Agent recognizes: stress signal, time context
Looks up: relationship_type=friend, last_interaction=3_days_ago
Response: "Hey, I noticed you've been stressed lately. Maybe it's time for that vacation?"
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

## Related Documentation

| Document | Purpose |
|----------|---------|
| [SPEC-015](SPEC-015-AGENTIC_WORKFLOW.md) | Base agent architecture |
| [SPEC-073](SPEC-073-SHARED_LORE_ARCHITECTURE.md) | Long-term memory structure |
| [ADR-010](../adr/ADR-010-SIMPLIFIED_STACK_ARCHITECTURE.md) | Database design decisions |
