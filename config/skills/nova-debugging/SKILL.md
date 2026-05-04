---
name: nova-debugging
category: development
description: Debugging nova-agent sessions — handling loops, hallucinated tool calls, context drift, tool chain failures, and permission issues
---

# Nova Debugging

## Agent Is Looping or Stuck

Signs: nova calls the same tool repeatedly, keeps saying "let me try X" without progress, or hits iteration limit.

**Actions:**
1. `Ctrl+C` to interrupt the current turn
2. Diagnose: is nova stuck because a tool is failing, or because it misunderstood the task?
3. If tool failure — fix the underlying issue, then give a clearer instruction
4. If misunderstood — `/undo` to remove the bad exchange, then rephrase with explicit constraints

```
# After a loop, reset and redirect
"Stop. The approach of [what it was trying] isn't working because [reason].
Instead, do [specific alternative] — only that, nothing else."
```

## Hallucinated Tool Calls

Signs: nova calls a tool with invented parameters, references a file that doesn't exist, or uses a function signature that's wrong.

**Cause:** usually long context, ambiguous instruction, or nova inferring instead of reading.

**Fix:**
1. `Ctrl+C` → `/undo`
2. Be explicit: include exact file paths, function names, line numbers
3. Ask nova to read the file before acting on it: `"First read X, then proceed"`
4. If session is long: `/compact` before continuing

## Context Drift (Off-Task Behavior)

Signs: nova starts solving a different problem, refactors code you didn't ask about, or adds features beyond scope.

**Prevention:**
- Keep task descriptions tightly scoped
- Add explicit "don't touch X" or "only change Y" constraints
- Check `git diff` after each exchange

**Fix:**
```bash
git diff                   # see what actually changed
git restore <file>         # discard specific file changes
git restore .              # discard all unstaged changes
```

Then `/undo` in chat and rephrase with tighter scope.

## Tool Chain Failures

| Error pattern | Likely cause | Fix |
|---------------|-------------|-----|
| `Error: file not found` | Wrong path | Ask nova to search for the file first |
| `Error: patch string not found` | Stale `old_string` | Ask nova to re-read the file and retry |
| `Error: permission denied` | Blocked path or `ask` mode | Check `permissions` config |
| `Error: command timed out` | Long-running command | Use `task_create` for background execution |
| `mypy: N errors` | Type mismatch | Share the full error output, ask nova to fix each one |
| `pytest: FAILED` | Test regression | Run with `-v` to see full traceback, share with nova |

When a tool fails silently (nova ignores the error and continues), interrupt and make it explicit:
```
"The last tool call returned an error. Stop and fix that before continuing."
```

## Session Health

**Use `/compact` when:**
- Session is over 15–20 turns
- Nova is repeating itself or forgetting earlier decisions
- Responses are getting slower or less coherent

**Use `/new` when:**
- Switching to an unrelated task
- Nova is fundamentally confused about context
- A bad exchange can't be cleanly undone

**Use `/undo` when:**
- The last exchange went wrong and you want to retry differently
- Nova made an unintended change you want to roll back in both chat and code

## Verifying What Nova Actually Did

Always verify after a long or multi-step session before accepting the result:

```bash
git diff                    # all unstaged changes
git diff --staged           # staged changes
git diff HEAD~1             # last commit
git log --oneline -5        # recent commits
git stash                   # temporarily shelve if you need a clean slate to test
```

Never trust "I've completed the task" without checking `git diff`.

## Debugging Permission Issues

If a tool call is unexpectedly blocked:

1. Check `permissions.denied_tools` in `config.yaml`
2. Check `permissions.path_rules` for path-level blocks
3. Check built-in blocked paths: `~/.ssh/*`, `~/.aws/*`, `~/.gnupg/*`, `~/.kube/config`
4. Check `permissions.mode` — in `ask` mode, mutating tools need confirmation

```bash
# Confirm what mode is active
nova ask "what is the current permissions mode?"
```

## Debugging Context / Token Issues

```
/status      — session info, token count, model, depth
/usage       — token usage and dollar cost for this session
```

If compression is triggering too aggressively:
```yaml
budgets:
  conversation_turn_limit: 20    # default 15 — increase for longer sessions
compression:
  threshold_percent: 0.60        # default 0.40 — compress less aggressively
```

If responses are slow or context feels stale after compression, `/new` and paste only the relevant context back in.

## Debugging a Failing CI Check

```bash
# Run each step independently to isolate the failure
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy nova/
.venv/bin/pytest -x -v          # stop on first failure, verbose

# If ruff format fails — apply the fix
.venv/bin/ruff format .

# If mypy fails — show full output
.venv/bin/mypy nova/ 2>&1 | head -50

# If pytest fails — run the specific failing test
.venv/bin/pytest tests/test_foo.py::test_bar -v -s
```

Share the full error output with nova — partial output leads to partial fixes.
