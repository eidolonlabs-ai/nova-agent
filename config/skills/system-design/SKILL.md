---
name: system-design
category: engineering
description: System design — architecture, components, data models, API contracts, trade-offs, and ADRs. Use when designing a new system, feature, or integration before implementation.
---

# System Design Skill

Design systems deliberately before coding. Produce a design that a reviewer can critique without reading implementation code.

## Design Workflow

1. **Restate the problem** — 2–3 sentences; note constraints (scale, latency, cost, team size)
2. **Identify stakeholders & interfaces** — who calls this, what calls it, what does it call?
3. **Sketch components** — boxes and arrows; one responsibility per box
4. **Define the data model** — entities, relationships, ownership, lifecycle (who creates/deletes?)
5. **Define API contracts** — signatures, schemas, error semantics, idempotency
6. **List trade-offs** — 2+ options per significant decision, with a recommendation
7. **Write an ADR** for each significant decision (see documentation-template-builder for the ADR template)

## Component Design

- One component = one responsibility. If a box has "and" in its description, split it
- Draw the data flow: request → validation → business logic → storage → response
- Show failure paths in the diagram too — what happens when a dependency is down?
- Keep dependencies acyclic; a component must not depend on its dependents

## Data Model Rules

- Define ownership explicitly — every entity has exactly one owning service/module
- Use the schema of the storage layer; don't smuggle presentation concerns into it
- Prefer immutable or append-only records for audit-sensitive data
- Indexes follow query patterns, not column naming — design queries first, then indexes

## API Contract Rules

- Contract-first: write the interface before the implementation
- Every endpoint/function: inputs, outputs, errors, side effects
- Idempotency keys for any operation that can be retried safely
- Version externally visible APIs; don't break callers silently
- Define pagination, rate limits, and timeouts for anything remote

## Trade-off Table

```markdown
| Decision | Option A | Option B | Recommendation |
|----------|----------|----------|----------------|
| Storage   | Postgres | SQLite   | Postgres — concurrent writers |
| Sync      | REST     | gRPC     | REST — external consumers, low QPS |
```

Each row needs a *reason*, not just a pick.

## ADR Requirements

Record every decision with lasting consequences:
- Context (what prompted this)
- Options considered (at least 2)
- Decision + rationale
- Consequences (what we accept, what we give up)

## Pitfalls

- Don't skip the data model — schema decisions are the hardest to reverse
- Don't design for hypothetical scale — note the assumption and move on ("YAGNI")
- Don't invent new abstractions when the existing architecture already has a pattern
- Don't leave the error/failure path undesigned — it's where production bugs live
- Don't merge a design with no ADR for a significant choice — future devs will re-litigate it
