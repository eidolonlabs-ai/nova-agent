---
name: code-review
category: development
description: How to review code — what to check, how to pull PR context, and how to phrase feedback
---

# Code Review Skill

## Pulling PR Context

Before reviewing, gather the full picture:

```bash
gh pr view 42                  # title, description, author, CI status
gh pr diff 42                  # full unified diff
gh pr checks 42                # CI pass/fail status
gh pr list --state open        # all open PRs
```

For nova-agent, also verify the CI invariants manually if CI is not available:

```bash
ruff check .                   # must be clean
mypy nova/                     # must be 0 errors
pytest                         # all 557 tests must pass
```

## What to Check

### Correctness (blocking)
- Does the logic actually do what the PR description claims?
- Are edge cases handled — empty input, None, missing files, API errors?
- Are error paths returning error strings, not raising exceptions (nova tool convention)?
- Does any new tool handler follow the `(args: dict, **kwargs) -> str` signature?

### Types and Lint (blocking)
- All public functions have type annotations
- No new `mypy` errors (`mypy nova/`)
- No new `ruff` errors (`ruff check .`)

### Tests (blocking)
- New features have tests
- New tools have handler tests with mock injected deps (no real HTTP, no real DB)
- Tests cover error paths, not just happy paths
- Test names follow `test_<what>_<when>` pattern

### Design (discuss, not always blocking)
- Is the change scoped correctly — does it do one thing?
- Are there obvious abstractions being skipped or unnecessary ones being added?
- Is the tool description in the schema accurate and concise?
- Does the skill/tool fit the existing architecture (see `nova/tools/` patterns)?

### Security
- No secrets, API keys, or credentials in code
- No shell injection risk in commands built from user input
- Prompt injection scanning is in place for any new content-loading code

## What to Skip

Don't nitpick:
- Style preferences that ruff doesn't enforce
- Minor naming variations that are still clear
- Comment phrasing
- Tests that are redundant but harmless
- Ordering of imports within a group

## How to Phrase Feedback

Use a prefix to signal severity:

| Prefix | Meaning |
|--------|---------|
| **blocking:** | Must fix before merge |
| **suggestion:** | Worth discussing, not required |
| **nit:** | Minor, author's call |
| **question:** | Genuinely unsure, asking for context |

Examples:
```
blocking: `execute_terminal` doesn't handle the case where `workdir` is a symlink to a missing path — this will crash.

suggestion: this could use the existing `_truncate_output` helper instead of reimplementing truncation.

nit: `get_skill_path` → `skill_path` reads slightly cleaner.

question: why does this need to parse frontmatter again here rather than reusing the cached result?
```

## Review Workflow

1. Read `gh pr view 42` — understand intent before reading code
2. Read `gh pr diff 42` — look at the whole diff before commenting on parts
3. Run CI checks locally if they aren't green
4. Leave comments grouped by file/concern, not line-by-line nitpicking
5. Summarize at the end: approve, request changes, or ask a question

```bash
# Approve
gh pr review 42 --approve --body "LGTM. Tests look solid."

# Request changes
gh pr review 42 --request-changes --body "blocking: see inline comments on error handling"

# Comment only
gh pr review 42 --comment --body "Looks close — one question before I approve"
```

## Nova-Specific Conventions

- Tools live in `nova/tools/` and register via `registry.register()`
- Tool handlers return strings — errors are `"Error: ..."`, never exceptions
- Tests use dependency injection: `NovaAgent(http_client=mock, session_store=mock, memory_store=mock)`
- Skills live in `config/skills/<name>/SKILL.md` with YAML frontmatter
- Commit messages follow conventional commits (`feat:`, `fix:`, `test:`, etc.)
- Coverage target is 80%+ for new code; check with `pytest --cov=nova`
