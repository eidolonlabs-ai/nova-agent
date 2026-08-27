---
name: refactoring
category: development
description: Safe refactoring — behavior-preserving changes, seams, incremental steps, and verification with the existing test suite
---

# Refactoring Skill

Refactoring changes structure, not behavior. If behavior changes, it's a feature or a fix — different commit.

## Rules

- **Never refactor and change behavior in the same commit** — two separate changes, two reviews
- **The test suite is your safety net** — if the suite is thin, add characterization tests before refactoring
- **Small steps** — each step compiles, passes tests, and can be its own commit
- **One concern at a time** — rename everything, then move things, then change structure; don't mix

## Safe Refactoring Workflow

1. **Baseline** — run the full test suite; it must be green before you start
2. **Add characterization tests** — for untested behavior, write tests that pin current output (even if ugly) before touching code
3. **Find seams** — the narrowest places where structure can change without touching callers
4. **Apply one mechanical transformation at a time** — rename, extract, inline, move
5. **Run the suite after every step** — red means the step was wrong, not "continue anyway"
6. **Commit per step** — `refactor: rename X to Y` / `refactor: extract Z`

## High-Value Refactorings

- **Extract function/method** — when a block has a clear name and is longer than ~10 lines
- **Rename** — when a name lies about what the thing does (the most valuable refactoring)
- **Introduce parameter object** — when 3+ args travel together
- **Replace magic values with named constants**
- **Remove dead code** — delete it, don't comment it out; git history preserves it
- **Reduce nesting** — early returns / guard clauses

## Using Tools

- Python: `ruff check --fix`, `ruff format`, and IDE rename/refactor commands
- `grep`/`search_files` to find all references before a rename — rename must be exhaustive
- `git diff` after each step to confirm only the intended lines changed

## Pitfalls

- Don't refactor code you don't understand — understand it, characterize it, then refactor
- Don't do drive-by refactoring inside feature commits — it buries review intent
- Don't skip the suite between steps — the step that breaks is cheap to find, the pile isn't
- Don't refactor public APIs without a deprecation path — external callers exist
- Don't rename things in docs and code in separate PRs — keep them together
