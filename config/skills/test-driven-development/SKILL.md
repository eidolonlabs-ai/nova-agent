---
name: test-driven-development
category: testing
description: TDD workflow — red-green-refactor cycles, test pyramid, mocking, coverage gates, and which layer each test belongs in
---

# Test-Driven Development Skill

Write the test first, watch it fail, write the minimum code to pass, then refactor. This is not optional ceremony — it is how you get a suite that documents behavior.

## The Cycle

1. **Red** — write one failing test for the next behavior. Run it; confirm it fails for the *right* reason (assertion, not import error)
2. **Green** — write the minimum code to pass. No extra features, no "while I'm here" changes
3. **Refactor** — clean up while keeping tests green. Run the full suite
4. Repeat. One behavior per cycle. Small commits: `test: add X`, then `feat: make X pass`

## What to Test First

- The interesting logic — pure functions, business rules, edge cases
- Error paths: empty input, `None`, malformed data, missing files, timeouts
- Boundary values: zero, negative, max, first/last of a range
- Anything that has ever been a bug before — regression tests are forever

## Test Pyramid

| Layer | Count | Speed | Purpose |
|-------|-------|-------|---------|
| Unit | Most | ms | One function/class in isolation |
| Integration | Some | s | Modules working together (real DB/files) |
| E2E | Few | min | Full user flows through real interfaces |

- Put a test at the lowest layer that can catch the bug
- Unit tests must not need network, real DBs, or real clocks — inject fakes

## Mocking Rules

- Mock at boundaries only: HTTP clients, filesystem, time, random, subprocess
- Never mock the code under test's own internals — that tests the mock
- Assert on calls with meaningful arguments, not just "was called"
- Prefer dependency injection over `patch`/monkeypatching when you control the code

```python
# inject the client — no patching needed
agent = NovaAgent(http_client=FakeClient(...), session_store=MemoryStore())
```

## Coverage Gates

- New code targets 80%+ line coverage (`pytest --cov=nova --cov-report=term-missing`)
- Coverage is a floor, not a goal — test behavior, don't chase the last 5% with tautological tests
- Never add `# pragma: no cover` to hide untested code; use it only for genuinely unreachable branches (e.g., `if TYPE_CHECKING`)

## Naming & Structure

- Files: `test_<module>.py` next to the module or in `tests/`
- Functions: `test_<what>_<when>` — reads like a spec: `test_cart_total_with_discount_applies_tax`
- One assertion cluster per test; if you're testing three behaviors, write three tests
- Use fixtures for shared setup; keep them in `conftest.py`

## Pitfalls

- Don't test implementation details — assert on behavior and results, not call counts
- Don't delete a failing test to make the suite green — fix the code
- Don't skip error paths — happy-path-only suites pass CI and break in prod
- Don't assert on exact error message strings unless the message is the contract
- Don't write tests that depend on test execution order or shared mutable state
