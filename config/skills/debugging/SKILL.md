---
name: debugging
category: development
description: Debugging workflow — reproduce, isolate, bisect, instrument with logging/pdb, root-cause analysis, and performance profiling
---

# Debugging Skill

Debugging is a method, not a mood. Never guess — reproduce, isolate, and verify.

## Workflow

1. **Reproduce** — get a minimal, reliable reproduction before touching anything
2. **Read the error** — full traceback, first. The last frame is where it broke; the *cause* is usually higher up
3. **Form a hypothesis** — one at a time, with a prediction you can test
4. **Isolate** — binary search the input space and the code path (comment out halves, not lines)
5. **Fix the root cause** — not the symptom. A fix that hides the error is a bug you'll meet again
6. **Add a regression test** — the bug must never come back

## Binary Search

- Bisect commits: `git bisect start && git bisect bad && git bisect good <sha>` — feed `git bisect good/bad` until it names the culprit
- Bisect data: shrink input, config, or the call path until the failure disappears — the boundary is where the bug lives
- Bisect code: comment out half the pipeline, not individual lines

## Instrumentation

- **Logging over print**: use the project's logger; include context (ids, inputs, timings)
- **pdb** for interactive poking:

```bash
python -m pdb script.py
# or break on a line:
python -m pdb -c "break nova/agent.py:440" -c "continue" script.py
```

- In tests: `pytest -x --pdb` drops into the debugger on first failure
- `traceback.print_exc()` in handlers — but prefer returning structured errors (nova tool convention)

## Intermittent Failures

- Run the test in a loop: `pytest test_x.py -x --count=50` (needs `pytest-repeat`)
- Suspect, in order: shared mutable state, ordering, time/clock dependence, randomness, concurrency, unclosed resources
- Add `random.seed()` / `time.time()` injection points so races become reproducible

## Performance Profiling

- Profile, don't guess: `python -m cProfile -s cumulative script.py | head -30`
- Memory: `python -m tracemalloc` or `memray`/`memory_profiler` for leaks
- Compare timings before/after any optimization — "it feels faster" is not data
- Look for: N+1 loops, repeated work in hot paths, accidental O(n²), blocking calls in async code

## Pitfalls

- Don't "fix" an error you haven't reproduced — you'll fix the wrong thing
- Don't shotgun-edit ("try changing this and that") — one hypothesis at a time
- Don't delete the failing test or the error log — they're the evidence
- Don't fix symptoms with `try/except: pass` — if the error is ignorable, say why in a comment
- Don't leave debug prints behind — remove instrumentation before committing
