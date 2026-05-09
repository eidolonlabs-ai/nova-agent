# GUIDE-011: Context Compression

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** GUIDE (Developer & User Reference)

> Nova Agent uses a three-tier strategy to manage context windows efficiently. Each tier is progressively more aggressive — Nova escalates only when the budget is exceeded.

---

## Quick Start

Context compression is automatic. You don't need to configure anything. But if you want to control it:

```yaml
context:
  budget: 128000        # total token budget
  threshold_percent: 85 # trigger compression at 85%
  preserve_recent: 6    # always keep these many messages intact
```

Or trigger it manually in chat:

```
/compact
```

---

## The Three-Tier Strategy

Nova uses a cascade approach — each tier is cheaper (in time and tokens) than the last, but also more lossy.

| Tier | Method | Cost | Loss | Trigger |
|------|--------|------|------|---------|
| **1** | Microcompact — strip old tool content | Free (no LLM call) | Low | Budget > 85% |
| **2** | LLM compress — summarize older messages | Medium (one LLM call) | Medium | Budget > 95% |
| **3** | Session reset | N/A | High | User runs `/new` or `/reset` |

### Tier 1: Microcompact

**What it does:** Replaces the content of old tool call results with short placeholders like `[tool result stripped — 2,340 tokens]`. The message structure stays intact so the model still understands the conversation flow, just without the raw output.

**Why it's first:** It's free — no LLM call needed. It preserves 100% of the conversation structure while reclaiming ~60–80% of tool result tokens.

**What it preserves:**
- System messages
- User messages
- Assistant messages
- Message order and roles

**What it strips:**
- Old tool result content (replaced with a placeholder showing token count)
- Tool results beyond `preserve_recent` count

**Trade-offs:**
- ✅ No extra latency or cost
- ✅ Preserves conversation flow
- ❌ Loses detailed tool output (code, file contents, search results)
- ❌ The model can't reference stripped content

### Tier 2: LLM Context Compression

**What it does:** Calls the LLM to produce a concise summary of older messages. The summary is injected as a single system-level message. Recent messages stay intact.

**Summary preserves:**
1. User's original goals and requests
2. Key decisions and conclusions
3. File paths, code snippets, technical details
4. Errors encountered and resolutions
5. Current state of work and remaining tasks

**What it discards:**
- Conversational filler and pleasantries
- Failed attempts that were superseded
- Detailed tool output (summarized instead)

**Trade-offs:**
- ✅ Much more information preserved than microcompact
- ✅ One LLM call, not per-message
- ❌ Extra latency (~1–3 seconds)
- ❌ Extra tokens consumed for the summary call itself
- ❌ Summary may miss subtle details

### Tier 3: Session Reset

**What it does:** Starts fresh with a clean session. The previous session is saved to the SQLite database for later retrieval via `/sessions` and `/resume`.

**When to use:**
- The current session has drifted or is producing poor results
- Context is full of irrelevant information
- You want a clean slate for a new task

**How to recover:** Use `/sessions` to list past sessions, then `/resume [id]` to pick up where you left off.

---

## Configuration

All context settings live under `context:` in `config.yaml`:

| Setting | Default | Description |
|---------|---------|-------------|
| `budget` | 128000 | Total token budget (model's context window) |
| `threshold_percent` | 85 | Trigger microcompact at this % of budget |
| `preserve_recent` | 6 | Always keep this many messages untouched |

### Example Configurations

**Conservative (long sessions, more detail preserved):**
```yaml
context:
  budget: 128000
  threshold_percent: 90
  preserve_recent: 10
```

**Aggressive (shorter sessions, cleaner context):**
```yaml
context:
  budget: 128000
  threshold_percent: 75
  preserve_recent: 4
```

---

## How It Works in Practice

Here's what happens during a long conversation:

```
Message 1–50  → Full tokens: 25,000 / 128,000 (19%) — nothing happens
Message 51–100 → Full tokens: 85,000 / 128,000 (66%) — nothing happens
Message 101–150 → Full tokens: 110,000 / 128,000 (86%) → Tier 1: microcompact
Message 151–200 → Full tokens: 124,000 / 128,000 (97%) → Tier 2: LLM compress
Message 201+   → User runs /new → Tier 3: session reset
```

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Context keeps compressing too early | `threshold_percent` too low | Increase to 90 |
| Losing important details after compression | Too many tiers applied | Increase `preserve_recent` |
| Session feels "empty" after /compact | Tier 2 summary missed details | Try `/resume` instead |
| Compression is slow | Tier 2 LLM call on a slow model | Use a faster model for compression |

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [GUIDE-003 Customizing](GUIDE-003-CUSTOMIZING.md) | All config options |
| [GUIDE-005 Cost Tracking](GUIDE-005-COST_TRACKING.md) | How compression affects cost |
| [GUIDE-009 Using Nova](GUIDE-009-USING_NOVA.md) | `/compact` and `/new` commands |
| [SPEC-017 LLM Robustness](ADR-003-TOOL_SYSTEM_REVIEW.md) | Compression design decisions |
