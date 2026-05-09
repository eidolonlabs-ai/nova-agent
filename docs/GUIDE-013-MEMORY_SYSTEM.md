# GUIDE-013: Memory System

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** GUIDE (Developer & User Reference)

> Nova Agent includes a file-based memory system for storing durable facts across sessions. Unlike conversation history (which gets compressed and truncated), memory persists indefinitely.

---

## Quick Start

### For Users (in chat)

```
User: Remember that I prefer Python 3.12 for projects
Assistant: [calls memory tool with action="add", content="Prefers Python 3.12 for projects", category="general"]
Assistant: Got it — remembering that you prefer Python 3.12.

User: What do you know about my preferences?
Assistant: [calls memory tool with action="search", query="preferences"]
Assistant: I remember:
- You prefer Python 3.12 for projects
```

### For Developers (programmatic)

```python
from nova.memory import MemoryStore
from pathlib import Path

store = MemoryStore(Path("~/.nova/memory.json"), max_entries=100)

# Add a fact
store.add("User prefers async/await over callbacks", category="preferences")

# Search
results = store.search("python")
# Returns: [{"content": "User prefers Python 3.12...", "category": "preferences", ...}]

# Delete
store.delete(entry_id)

# Clear all
store.clear()
```

---

## How Memory Works

Memory is Nova's long-term learning system. Unlike conversation history, which is subject to token budgets and compression, memory entries persist across sessions and restarts.

### Architecture

```
MemoryStore (Python class)
    └── memory.json (file on disk)
        ├── { "content": "...", "category": "...", "created_at": "..." }
        ├── { "content": "...", "category": "...", "created_at": "..." }
        └── ...
```

**Storage:** Single JSON file — no database, no external dependencies.

**Operations:**
- **Add** — Append a new entry
- **Search** — Full-text scan of all entries
- **Delete** — Remove by entry ID
- **Clear** — Wipe all entries

### Categories

Entries are tagged with categories for organization:

| Category | Use Case | Example |
|----------|----------|---------|
| `general` | Default, no special meaning | "User's name is Mark" |
| `preferences` | User preferences | "Prefers Python 3.12" |
| `project` | Project-specific facts | "Database is PostgreSQL" |
| `environment` | System/environment details | "Running on macOS Sonoma" |
| `context` | Session-specific context | "Working on feature X" |

---

## LRU Eviction

When the store reaches `max_entries` (default: 100), the **oldest** entries are evicted first. This is a simple LRU policy — no sophistication, no scoring, no ML. Just "oldest out."

```
Entry 1 (Jan 2026)  → Evicted (oldest)
Entry 2 (Feb 2026)  → Evicted
...
Entry 100 (May 2026) → Retained (newest)
```

**Trade-offs:**
- ✅ Simple, predictable, no tuning needed
- ❌ No notion of "importance" — a critical fact from 3 months ago gets evicted the same as a throwaway
- ❌ No deduplication — same fact stored twice counts as two entries

---

## Memory vs. Context vs. Skills

It's easy to confuse these three. Here's how they differ:

| System | Purpose | Lifetime | Source |
|--------|---------|----------|--------|
| **Context** | Current conversation state | Single session (compressed over time) | Conversation flow |
| **Memory** | Cross-session facts | Indefinite (until evicted) | Explicit user input |
| **Skills** | Domain knowledge | Indefinite | SKILL.md files |

### When to use each

- **Context** — "Let's debug this function together" → everything stays in context
- **Memory** — "Remember that I use a MacBook Pro" → persists across sessions
- **Skills** — "Write Python following PEP 8" → always available, loaded on demand

---

## Configuration

Memory settings live in `config.yaml`:

```yaml
memory:
  max_entries: 100    # number of entries before LRU eviction starts
  file_path: "~/.nova/memory.json"  # where to store the file
```

### End Users

Memory is enabled by default. No config needed.

### Developers

```python
from nova.memory import MemoryStore

# Custom path and size
store = MemoryStore(
    Path("/tmp/my-memory.json"),
    max_entries=50
)
```

---

## Best Practices

### For Users

1. **Be specific** — "User prefers Python 3.12" is better than "User likes Python"
2. **Use categories** — Group related facts so searches are more targeted
3. **Don't over-save** — Only store facts you'll actually need later
4. **Review periodically** — Use `/sessions` to see what you've saved; delete stale entries

### For Developers

1. **Atomic writes** — MemoryStore uses `os.replace()` for atomic writes (safe against crashes)
2. **Graceful loading** — Corrupted JSON files are logged and reset to empty (no crash)
3. **Thread safety** — MemoryStore is NOT thread-safe. Wrap with a lock if accessing from multiple threads
4. **Search is linear** — With 100 entries, linear scan is fine. If you need 10K+ entries, consider a proper index

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Memory not persisting | File path doesn't exist or isn't writable | Check `memory.file_path` in config; ensure directory exists |
| Too many entries lost | LRU eviction kicked in | Increase `max_entries` or prune old entries |
| Memory seems "forgotten" | Category mismatch in search | Search with the right category keyword |
| JSON file is corrupted | Crash during write | MemoryStore handles this gracefully — reloads as empty |
| Memory is slow | Too many entries (>500) | Increase `max_entries` threshold or prune |

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [GUIDE-003 Customizing](GUIDE-003-CUSTOMIZING.md) | Config options |
| [GUIDE-011 Context Compression](GUIDE-011-CONTEXT_COMPRESSION.md) | How context differs from memory |
| [GUIDE-012 Session Management](GUIDE-012-SESSION_MANAGEMENT.md) | Session storage (separate from memory) |
| [GUIDE-009 Using Nova](GUIDE-009-USING_NOVA.md) | Memory tool usage in chat |
