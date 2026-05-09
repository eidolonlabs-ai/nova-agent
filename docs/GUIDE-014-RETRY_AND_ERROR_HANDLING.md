# GUIDE-014: Retry & Error Handling

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** GUIDE (Developer Reference)

> Nova Agent handles API failures gracefully with configurable retry logic, exponential backoff, and intelligent error classification. This guide explains how retries work and how to tune them.

---

## Quick Start

Retry logic is enabled by default. No configuration needed for typical use.

```yaml
retry:
  enabled: true
  max_retries: 3
  backoff_multiplier: 2      # 1s, 2s, 4s, 8s...
  jitter: true               # add randomness to prevent thundering herd
```

---

## Error Classification

Nova classifies every error into one of four categories, each with different retry behavior:

| Error Type | Behavior | Examples |
|------------|----------|----------|
| **Retryable** | Retry with exponential backoff | 429 rate limit, 500/502/503/504 server errors |
| **Non-retryable** | Fail immediately | 400 bad request, 401 unauthorized, 403 forbidden |
| **Context overflow** | Trigger compression, don't retry | Context window exceeded |
| **API timeout** | Retry once only | "timeout", "temporary failure" |
| **Connection timeout** | Retry with backoff | "connection refused", "connection reset" |

### HTTP Status Codes

| Status | Classification | Action |
|--------|---------------|--------|
| 400 | Non-retryable | Fail immediately |
| 401 | Non-retryable | Fail immediately |
| 403 | Non-retryable | Fail immediately |
| 429 | Retryable | Backoff + retry |
| 500 | Retryable | Backoff + retry |
| 502 | Retryable | Backoff + retry |
| 503 | Retryable | Backoff + retry |
| 504 | Retryable | Backoff + retry |
| 529 | Retryable | Backoff + retry |

### Error Message Patterns

String matching catches errors that don't have HTTP status codes (e.g., SDK-level errors):

```python
# Retryable patterns
"rate limit", "too many requests", "server error", "internal error",
"bad gateway", "service unavailable", "upstream error"

# Connection error patterns (retried aggressively)
"connection timeout", "connection refused", "connection reset"

# API timeout patterns (retried only once)
"timeout", "temporary failure", "gateway timeout"
```

---

## Retry Algorithm

The retry logic uses **exponential backoff with jitter**:

```python
wait_time = base_delay * (backoff_multiplier ** attempt) + random_jitter
```

### Default Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `base_delay` | 1 second | Starting delay before first retry |
| `max_retries` | 3 | Maximum number of retry attempts |
| `backoff_multiplier` | 2 | Exponential growth factor |
| `jitter` | true | Add ±25% random jitter |

### Example Timeline

With defaults (`max_retries: 3`, `multiplier: 2`, `jitter: true`):

```
Attempt 1: 0s      → 429 Too Many Requests
Attempt 2: ~1.5s   → 503 Service Unavailable
Attempt 3: ~4.2s   → 500 Internal Server Error
Attempt 4: ~9.8s   → 200 OK ✅
```

Without jitter, retries from multiple clients would hit the server simultaneously ("thundering herd"). Jitter spreads them out.

---

## Configuration

### Global Config

```yaml
retry:
  enabled: true               # set to false to disable retries entirely
  max_retries: 3              # max retry attempts per call
  base_delay: 1               # seconds before first retry
  backoff_multiplier: 2       # exponential factor
  jitter: true                # add randomness to prevent thundering herd
  max_delay: 30               # cap retry delay at this many seconds
```

### Example Configurations

**Aggressive retries (unreliable API):**
```yaml
retry:
  max_retries: 5
  base_delay: 2
  backoff_multiplier: 2
  jitter: true
  max_delay: 60
```

**Fast failures (don't wait around):**
```yaml
retry:
  max_retries: 1
  base_delay: 0.5
  backoff_multiplier: 1.5
  jitter: true
```

**No retries (fail fast, handle manually):**
```yaml
retry:
  enabled: false
```

---

## Context Overflow Handling

When the context window is exceeded, retrying won't help. Nova handles this specially:

1. **Detect** — API returns an error indicating context overflow
2. **Compress** — Trigger context compression (see [GUIDE-011](GUIDE-011-CONTEXT_COMPRESSION.md))
3. **Retry** — Re-attempt with the compressed context
4. **Escalate** — If still overflowing after compression, fail with a clear message

This is different from normal retries because it changes the request, not just re-sends it.

---

## Logging

Retry attempts are logged at the `INFO` level. Failed retries after exhausting all attempts are logged at `WARNING`.

```
[INFO] Retrying API call (attempt 2/3) after 429: rate limit exceeded
[INFO] Retrying API call (attempt 3/3) after 503: service unavailable
[WARNING] API call failed after 3 retries: 500 Internal Server Error
```

Set `NOVA_LOG_LEVEL=DEBUG` for detailed retry timing:

```
[DEBUG] Retry attempt 2 — waiting 1.83s (base=1.0, mult=2.0, jitter=+0.83)
[DEBUG] Retry attempt 3 — waiting 4.12s (base=2.0, mult=2.0, jitter=+0.12)
```

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Too many retries | API is genuinely down | Set `max_retries: 1` for faster failure |
| Retries are too slow | High `base_delay` or `max_delay` | Reduce `base_delay` to 0.5 |
| Thundering herd on API recovery | Multiple clients retrying simultaneously | Keep `jitter: true` (default) |
| Non-retryable errors being retried | Custom error classification needed | Check error patterns in `retry.py` |
| Context overflow causing retries | Session is too long | Run `/compact` to free tokens |

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [GUIDE-003 Customizing](GUIDE-003-CUSTOMIZING.md) | All config options |
| [GUIDE-011 Context Compression](GUIDE-011-CONTEXT_COMPRESSION.md) | Context overflow handling |
| [GUIDE-005 Cost Tracking](GUIDE-005-COST_TRACKING.md) | How retries affect cost |
| [ADR-003 Tool System Review](ADR-003-TOOL_SYSTEM_REVIEW.md) | Retry design decisions |
