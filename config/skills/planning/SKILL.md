---
name: planning
category: engineering
description: "Software planning — turn requirements into actionable work: user stories, acceptance criteria, task breakdown, estimation, and definition of done. Use before writing any code."
---

# Planning Skill

Turn vague requests into a concrete, executable plan before any code is written.

## Workflow

1. **Clarify the goal** — what problem are we solving, for whom, and what does "done" look like?
2. **Write user stories** — `As a <role>, I want <capability>, so that <benefit>`
3. **Define acceptance criteria** — observable, testable outcomes, one bullet each
4. **Break down tasks** — each task should be independently mergeable and reviewable
5. **Estimate** — small/medium/large (or story points); flag anything larger than ~1 day of work for splitting
6. **Define done** — tests pass, lint clean, docs updated, CI green, reviewed

## User Story Rules

- One story = one vertical slice of value — not a horizontal layer ("implement the DB schema")
- If a story needs 3+ subtasks, it's probably two stories
- Acceptance criteria are `given/when/then` or plain observable statements:

```
AC: Given an empty cart, when the user adds an item, then the cart shows 1 item and total = item price.
```

## Task Breakdown Template

```markdown
## [Story title]
**Goal:** one sentence
**Acceptance criteria:**
- [ ] ...
**Tasks:**
- [ ] Task 1 (small) — one-line description
- [ ] Task 2 (medium) — one-line description
**Out of scope:** what we are NOT doing (avoid scope creep)
```

## Estimation

- Small = < 4h, Medium = < 1 day, Large = 1–3 days
- Anything over 3 days must be split — you don't understand it well enough yet
- Re-estimate after each task completes; estimates are forecasts, not promises

## Sequencing Rules

- Identify the **critical path** — what must land first to unblock everything else
- Prefer vertical slices: end-to-end thin versions over deep single-layer work
- Put risky or unknown work early (fail fast), not at the end
- Never plan a task that depends on an unverified assumption — verify assumptions first with a spike

## Pitfalls

- Don't write code before acceptance criteria exist — you'll build the wrong thing
- Don't plan "implement the whole feature" as one task — split into shippable slices
- Don't forget non-functional requirements: performance, security, observability, docs
- Don't estimate in hours as if you'll be precise — use ranges or T-shirt sizes
- Don't put refactoring or cleanup in a feature story — file separate chores
