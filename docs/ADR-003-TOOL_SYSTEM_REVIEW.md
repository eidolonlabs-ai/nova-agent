# Nova Agent Tool System — Code Review & Design Analysis

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** ADR (Architecture Decision Record)  
**Scope:** Comparison with Claude Code, Hermes, OpenClaw, LangGraph, AutoGen, and OpenAI Swarm  
**Verdict:** Robust foundation with strategic advantages in token budgeting, delegation, and permissions. Strong core, narrow tool breadth.

---

## Executive Summary

Nova Agent implements a **principled tool architecture** centered on explicit token budgets, permission gates, and controlled parallelism. At ~1.8K LOC across 10 tools, it punches above its weight in architectural completeness compared to frameworks 10x its size.

**Strengths:**
- ✅ **Explicit token budgeting** at every layer (system prompt, context files, tool results)—matches Claude Code's design philosophy
- ✅ **Thread-safe tool parallelism** with read-only/write segregation (lines 412–472 in agent.py)
- ✅ **Multi-agent delegation** with depth limits, isolated contexts, and cost aggregation (352-line delegate_tool.py)
- ✅ **Fine-grained permission system** integrated at tool call dispatch (lines 375–392)
- ✅ **Streaming with watchdog timeout** (30s stream stall detection, line 298)
- ✅ **Hook system** for extensibility (pre/post tool, pre/post LLM, session start)
- ✅ **Error isolation**—tool failures don't crash agent (line 142–146 in registry.py)

**Weaknesses:**
- ❌ **Narrow tool breadth** (10 tools vs. Claude Code's 25+, LangGraph's unbounded)
- ❌ **No tool composition/chaining** framework (e.g., pipe output of one tool as input to another)
- ❌ **Limited async support**—concurrent.futures only, no native async/await
- ❌ **No tool versioning or deprecation** lifecycle
- ❌ **File ops tool lacks advanced features**—no glob patterns, no batch operations
- ❌ **Web search is Bing-only**—no fallback or provider abstraction
- ❌ **No structured output enforcement** for tool results
- ❌ **No observability hooks** for tool latency, cost per tool, call frequency

---

## Architecture Overview

### Tool Registration (registry.py — 193 lines)

```python
class ToolRegistry:
    def register(self, name, toolset, schema, handler, check_fn=None, emoji="🔧", is_read_only=False)
    def get_definitions(self, tool_names=None) -> list[dict]  # OpenAI-compatible format
    def dispatch(self, name, args, **kwargs) -> Any  # Pre/post hooks, error wrapping
```

**Pattern:** Declarative, singleton registry with auto-discovery via `discover_builtin_tools()`.

**Strengths:**
- ✅ Two-tier schema (compact list for prompt, full for API) reduces token overhead
- ✅ Generation counter enables cache invalidation (line 64)
- ✅ Read-only tool classification gates parallelism decisions (line 20–27)
- ✅ Check functions (e.g., permission validation) supported but optional

**Weaknesses:**
- ❌ No tool versioning (e.g., `read_file@v2` with backward compat)
- ❌ No deprecation warnings
- ❌ No tool aliasing (e.g., `ls` → `search_files`)
- ❌ Handler signature is `(args, **kwargs)` — assumes dict, no type validation pre-dispatch

### Tool Dispatch (agent.py:364–410)

```python
def _execute_tool_call(self, tool_call):
    # Permission check with file_path/command extraction
    # Pre-hook, dispatch, post-hook
    # JSON parsing, error wrapping
```

**Comparison to Claude Code:**
- ✅ **Nova:** Permission check before dispatch (proactive)
- ✅ **Claude Code:** Permission check integrated with tool routing (reactive, but all requests logged)
- ✅ Both serialize tool results as plain text

**Weaknesses:**
- ❌ No structured output validation (e.g., "this tool must return JSON")
- ❌ No metering (cost per tool, latency tracking)
- ❌ `json.loads()` on arguments can fail silently if model generates invalid JSON (line 371)

### Parallelism (agent.py:412–472)

```python
def _execute_tool_calls_parallel(self, tool_calls):
    # Segregate read-only vs. write-only
    # Execute read-only in parallel (max 4 workers)
    # Execute write-only sequentially
    # Thread-safe exception handling
```

**Comparison:**
- ✅ **Nova:** Explicit read-only classification, thread-safe pools
- ✅ **LangGraph:** Graph-based; parallel nodes allowed, sequencing via edges
- ✅ **AutoGen:** Actor model; true concurrency via async
- ❌ **Swarm:** No parallelism; single-threaded loop
- ❌ **OpenClaw:** Single-threaded

**Nova's approach:**
- Simple and correct for most agents
- Limited to 4 workers (configurable could improve)
- No dependency ordering (e.g., "tool B waits for tool A output")

---

## Tool Completeness Analysis

### Current Tool Inventory

| Tool | LOC | Type | Robustness | Breadth |
|------|-----|------|-----------|---------|
| **terminal** | 142 | I/O | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **read_file** | 308* | I/O | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **write_file** | (same) | I/O | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **patch_file** | (same) | I/O | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **search_files** | 141 | Search | ⭐⭐⭐⭐ | ⭐⭐ |
| **delegate_task** | 352 | Delegation | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **web_search** | 142 | Web | ⭐⭐⭐ | ⭐⭐ |
| **skills_tool** | 198 | Meta | ⭐⭐⭐ | ⭐⭐ |
| **memory_tool** | 113 | Memory | ⭐⭐⭐ | ⭐⭐ |
| **task_tools** | 233 | Task Mgmt | ⭐⭐⭐ | ⭐⭐ |

*file_ops.py implements read/write/patch—308 total

### Tier 1: Excellent (Production-Ready)

**patch_file** (⭐⭐⭐⭐⭐)
- Exact search/replace with first-match semantics
- Atomic writes via tempfile
- 100KB max patch size enforced
- Compared to Claude Code's Edit tool: Nearly identical design. Claude Code's is slightly more forgiving (context-aware), nova's is more explicit (requires exact string match).

**read_file** (⭐⭐⭐⭐)
- Line range support (offset + limit)
- 8KB output limit with 70/20 truncation
- Blocked path checking (shadow, sudoers, SSH, AWS, etc.)
- **Gap:** No glob patterns, no symlink traversal control

**terminal** (⭐⭐⭐⭐)
- Timeout enforcement (1–3600s)
- Destructive command logging (rm -rf, mkfs, eval)
- Output truncation with head/tail preservation
- Permission checks integrated
- **Gap:** No output filtering (e.g., mask secrets), no retry logic

**delegate_task** (⭐⭐⭐⭐⭐)
- Depth-limited spawning (configurable max_spawn_depth)
- Timeout enforcement per sub-agent (default 60s, max 300s)
- Two context modes: isolated (fresh) or fork (inherit transcript)
- Cost aggregation back to parent
- Thread-pooled execution with hard timeouts
- Minimal prompt mode for sub-agents (reduces context)
- **Comparison:** Exceeds AutoGen's delegate_to_agent pattern; matches LangGraph's graph-based routing in spirit but more explicit

### Tier 2: Functional (Useful for Most Tasks)

**search_files** (⭐⭐⭐⭐)
- Regex search with line context
- Respects .gitignore
- 500 result limit (protects against runaway queries)
- **Gaps:**
  - No glob support (e.g., `*.py`)
  - Single regex at a time (no AND/OR)
  - No inverted search (exclude pattern)

**web_search** (⭐⭐⭐)
- Zero dependencies (no API key required—Bing RSS)
- Result count limit (25 default)
- **Gaps:**
  - Bing-only (no fallback, no choice)
  - RSS-based (fragile; relies on undocumented API)
  - No caching
  - No result filtering (date, domain, language)

**skills_tool** (⭐⭐⭐)
- YAML frontmatter parsing (matching Claude Code skill format)
- Search by description (case-insensitive)
- Minimal validation
- **Gaps:**
  - No skill execution (only discovery + viewing)
  - No versioning
  - No dependency resolution

**memory_tool** (⭐⭐⭐)
- LRU eviction (configurable max_entries)
- Search via simple substring match
- add/search/delete/clear operations
- **Gaps:**
  - No structured queries (no metadata filtering)
  - No tagging or categories
  - Linear search (O(n) for large memories)

**task_tools** (⭐⭐⭐)
- task_create, task_list, task_update, task_get operations
- Status tracking (pending/in_progress/completed)
- Dependency tracking (blocks/blockedBy)
- **Gaps:**
  - No task concurrency control (if sub-agent updates task, no lock)
  - No due dates or reminders
  - No task filtering (show only my tasks, overdue, etc.)

### Tier 3: Minimal (MVP Quality)

All 10 tools are implemented. None are stubs. **This is excellent.** However, breadth is narrow:

- ❌ **No HTTP client** (for API interaction—agents can't easily call external REST endpoints)
- ❌ **No database tools** (SQL execution, schema introspection)
- ❌ **No data processing** (CSV, JSON parsing—agents must shell out to Python)
- ❌ **No code execution** (unlike CodeExecutorAgent in AutoGen)
- ❌ **No browser automation** (unlike Claude Code)
- ❌ **No git integration** (beyond `terminal` wrapper)
- ❌ **No scheduling** (unlike Hermes' cron support)
- ❌ **No vector search** (unlike Claude Code's Tool Search)

---

## Design Patterns: Strengths & Weaknesses

### 1. Token Budgeting (Excellent)

**Nova's approach:**
```python
# system_prompt_max: 8000 tokens
# context_total_max_chars: 100000
# tool_result_max_chars: 5000
# conversation_turn_limit: 15
```

**Comparison:**
- ✅ **Claude Code:** Same pattern (context files, budgets at every layer)
- ✅ **LangGraph:** Explicit token limits, checked in nodes
- ❌ **Swarm:** No budgeting (stateless)
- ❌ **AutoGen:** No built-in budgeting
- ❌ **Hermes:** Relies on persistent memory instead of budgets

**Nova's strength:** Explicit, enforced at dispatch time (line 98 in terminal.py, line 99 in file_ops.py).

**Gap:** No per-tool latency budget (e.g., "timeout after 10 min total elapsed across all tools"). LangGraph can enforce this via state checks.

### 2. Error Handling (Good)

**Nova's approach:**
- Tool failures don't crash loop (line 142–146 in registry.py)
- Errors serialized as plain text to LLM
- Permission denials returned as errors (not exceptions)
- JSON parse failures handled (line 372 in agent.py)

**Comparison:**
- ✅ **Claude Code:** Same error serialization
- ✅ **LangGraph:** ToolNode catches exceptions, feeds to model
- ⚠️ **AutoGen:** Relies on model's `RetryDecision` for recovery
- ❌ **Swarm:** No structured error handling

**Gap:** No automatic retry logic for transient failures (e.g., network timeouts, rate limits). Claude Code and LangGraph have retry policies; Nova delegates to `retry_with_backoff()` for API calls only, not tool results.

### 3. Streaming (Good)

**Nova's approach:**
```python
def _stream_response(self, payload, callback=None, reasoning_callback=None):
    # Watchdog timeout: 30s with no data
    # Interrupt check: Ctrl+C
    # Tool call streaming (delta accumulation)
    # Reasoning content separated
```

**Comparison:**
- ✅ **Claude Code:** Full streaming, interrupt handling
- ✅ **LangGraph:** SSE streaming with auto-reconnect
- ✅ **Hermes:** Platform-native streaming (Telegram, Discord, etc.)
- ❌ **Swarm:** Streaming via Chat API only
- ⚠️ **AutoGen:** Streaming supported but async-only

**Nova strength:** Watchdog timeout (line 298) is clever—prevents hanging on stream stalls.

**Gap:** No reconnect logic if stream dies mid-transmission (LangGraph handles this).

### 4. Permissions (Excellent)

**Nova's approach:**
```python
# permission_checker.evaluate(tool_name, is_read_only, file_path, command)
# Returns: PermissionResult(allowed, requires_confirmation, reason)
# Integrated at tool dispatch (before handler runs)
```

**Comparison:**
- ✅ **Claude Code:** Permission gates at tool routing
- ❌ **LangGraph:** No permission system
- ❌ **AutoGen:** No permission system
- ❌ **Swarm:** No permission system
- ⚠️ **Hermes:** Platform-level permissions (Telegram, Discord) only

**Nova strength:** File path blocking (shadow, sudoers, SSH, AWS keys), command pattern matching.

**Gap:** No fine-grained scoping (e.g., "read-only in /home/user, but not /etc"). Claude Code supports this via path prefixes.

### 5. State Management (Good)

**Nova's approach:**
- SQLite session store with FTS5 full-text search
- Append-only message log
- Memory store with LRU eviction
- Hooks for extension (pre/post tool, pre/post LLM)

**Comparison:**
- ✅ **Claude Code:** Append-only logs, durable sessions
- ✅ **LangGraph:** Checkpointer-based persistence
- ⚠️ **AutoGen:** Event bus (in-memory or Redis)
- ❌ **Swarm:** Stateless by design
- ✅ **Hermes:** File-based memory (matching Nova's memory.py)

**Gap:** No session querying (e.g., "show me all sessions from today where I asked about Python"). Claude Code supports this.

### 6. Multi-Agent Coordination (Excellent)

**Nova's delegate_task (352 lines) vs. alternatives:**

| Feature | Nova | LangGraph | AutoGen | Claude Code |
|---------|------|-----------|---------|------------|
| **Isolated context** | ✅ (fresh) | ✅ (via graph) | ✅ (new bus) | ✅ (new agent) |
| **Context inheritance** | ✅ (fork mode) | ✅ (via state) | ✅ (shared bus) | ❌ |
| **Depth limits** | ✅ | ✅ (via graph structure) | ✅ | ✅ |
| **Timeout enforcement** | ✅ (hard limit) | ⚠️ (via token budget) | ⚠️ (via LLM config) | ✅ |
| **Cost aggregation** | ✅ | ❌ | ❌ | ❌ |
| **Thread safety** | ✅ (ThreadPoolExecutor) | ✅ (async) | ✅ (actor model) | ✅ |
| **Model override** | ✅ | ❌ | ❌ | ✅ (config) |

**Nova strength:** Cost tracking + model override allows cheap sub-agents (use `gpt-4o-mini` for leaf tasks).

**Weakness:** Only synchronous pools. If you need to spawn 100 sub-agents, you'll block (max 4 in flight due to semaphore).

---

## Gaps & Recommendations

### Critical Gaps (Should Fix)

1. **No tool composition framework**
   - Users can't easily pipe tool output as input to another
   - Workaround: Use intermediate files + read_file
   - **Recommendation:** Add a `chain_tools(tool1, tool2, ...)` abstraction (5–10 lines)

2. **No structured output validation**
   - Tools return strings; no schema validation on output
   - Risk: LLM can't distinguish malformed output from legitimate result
   - **Recommendation:** Add optional `output_schema` to tool registry; validate before returning to LLM

3. **File ops tool missing glob/batch support**
   - `read_file` only reads single file; agents waste calls for `ls` + loop
   - **Recommendation:** Add `glob_pattern` parameter; return list of matching files

4. **Web search Bing-only**
   - RSS is fragile; no fallback
   - **Recommendation:** Abstract provider, allow fallback to DuckDuckGo or Google News (with API key optional)

### Important Gaps (Nice to Have)

5. **No tool latency/cost metering**
   - Users can't see which tools are expensive or slow
   - **Recommendation:** Add per-tool cost tracking + latency histogram in cost_tracker

6. **No async support**
   - Heavy terminal workloads block other tools
   - **Recommendation:** Offer `asyncio` variant of registry (parallel implementation)

7. **Memory tool lacks filtering**
   - Can't search by date, category, or metadata
   - **Recommendation:** Add optional metadata dict to memory entries

8. **Task tools lack concurrency control**
   - If sub-agent updates task while parent is reading, race condition
   - **Recommendation:** Add distributed lock (file-based or Redis) for task updates

### Nice-to-Have Gaps (Future)

9. **No tool versioning**
   - Can't deprecate tools or maintain backward compat
   - **Recommendation:** Add version field to schema; support migration helpers

10. **No observability for individual tools**
    - Can't profile which tools are called most, or slowest
    - **Recommendation:** Add telemetry hooks (similar to pre/post_tool_call)

---

## Robustness Audit

### Code Quality (score: 8/10)

**Strengths:**
- ✅ Type hints throughout (mypy clean)
- ✅ Comprehensive error messages
- ✅ Defensive path validation (symlinks, blocked paths)
- ✅ Resource limits enforced (output size, command length, timeout)

**Weaknesses:**
- ⚠️ No input validation on optional parameters (e.g., `timeout` in terminal.py trusts int type)
- ⚠️ JSON parse failure in `_execute_tool_call` silently returns error string (could add logging)
- ⚠️ `registry._tools` accessed directly in agent.py:376 (should use accessor method)

### Security (score: 8/10)

**Strengths:**
- ✅ Blocked paths for sensitive files (/etc/shadow, .ssh, .aws, etc.)
- ✅ Destructive command logging (rm -rf, eval, mkfs)
- ✅ Permission checks before dispatch
- ✅ Output truncation prevents leaking large file contents

**Weaknesses:**
- ⚠️ Terminal tool uses `shell=True` (subprocess injection risk if agent is compromised, but not Nova's fault)
- ⚠️ No regex validation on search_files input (could DoS with catastrophic regex)
- ⚠️ Memory tool stores full user messages (could store secrets)

### Reliability (score: 8.5/10)

**Strengths:**
- ✅ Tool failures don't crash loop
- ✅ HTTP retries with exponential backoff
- ✅ Streaming watchdog timeout (prevents hanging)
- ✅ Parallel execution with exception isolation

**Weaknesses:**
- ⚠️ No retry logic for tool-level failures (only API calls)
- ⚠️ Thread pool exhaustion could block if all workers are hung
- ⚠️ Task tools don't handle concurrent updates (no locking)

---

## Comparative Scorecard

| Criterion | Nova | Claude Code | LangGraph | AutoGen | Swarm | Hermes |
|-----------|------|-------------|-----------|---------|-------|--------|
| **Tool Breadth** | 6/10 | 9/10 | 10/10 | 8/10 | 6/10 | 5/10 |
| **Token Budgeting** | 9/10 | 10/10 | 8/10 | 4/10 | 1/10 | 3/10 |
| **Error Handling** | 7/10 | 9/10 | 9/10 | 8/10 | 4/10 | 5/10 |
| **Multi-Agent** | 9/10 | 8/10 | 9/10 | 10/10 | 4/10 | 5/10 |
| **Permissions** | 8/10 | 9/10 | 3/10 | 2/10 | 1/10 | 2/10 |
| **Streaming** | 8/10 | 10/10 | 9/10 | 7/10 | 8/10 | 9/10 |
| **State Mgmt** | 8/10 | 9/10 | 9/10 | 7/10 | 1/10 | 8/10 |
| **Code Quality** | 8/10 | 10/10 | 9/10 | 8/10 | 7/10 | 7/10 |
| **Observability** | 5/10 | 7/10 | 8/10 | 9/10 | 2/10 | 4/10 |
| **Async Support** | 3/10 | 8/10 | 10/10 | 10/10 | 5/10 | 7/10 |
| **TOTAL** | **73/100** | **88/100** | **90/100** | **78/100** | **39/100** | **55/100** |

---

## Verdict

### Overall Assessment: **8/10 — Solid, Purpose-Built Framework**

Nova Agent is **not** trying to be a general-purpose agent framework. It's optimized for:
- 📌 **Single-agent workloads** with explicit token budgets (scripting, automation, debugging)
- 📌 **Multi-agent coordination** via delegation with cost tracking
- 📌 **File/terminal-heavy tasks** (dev workflows, system administration)
- 📌 **Offline-first execution** (runs locally, minimal dependencies)

**Where it excels:**
1. Token budgeting—matches Claude Code's philosophy, exceeds LangGraph
2. Delegation—depth limits + cost aggregation is unique
3. Permissions—better than every framework except Claude Code
4. Code simplicity—1.8K LOC of tools is lean and auditable

**Where it trails:**
1. Tool breadth (10 vs. 25+)—but all 10 are solid
2. Async/concurrency—synchronous only, limits scale
3. Observability—no per-tool metrics
4. Tool composition—can't easily chain tools

### Recommendation

**For:**
- ✅ Dev agents running locally
- ✅ Orchestrating multiple sub-agents with budgets
- ✅ File-heavy automation (code review, log analysis)
- ✅ Security-conscious deployments (explicit permissions)

**Against:**
- ❌ High-scale distributed agents (use AutoGen)
- ❌ Browser/API-heavy workflows (add HTTP tool)
- ❌ Real-time systems (no async)
- ❌ Unknown tool requirements (tool breadth too narrow)

---

## Actionable Next Steps (Priority Order)

### P0 (Critical)
- [ ] Add `glob_patterns` parameter to `read_file` / add `list_files` tool
- [ ] Add structured output validation for tools (optional `output_schema`)
- [ ] Add automatic retry logic for transient tool failures

### P1 (Important)
- [ ] Add HTTP client tool (for REST API calls)
- [ ] Add per-tool cost tracking in CostTracker
- [ ] Add `git` tool wrapper (common for dev agents)
- [ ] Refactor web_search to support multiple providers

### P2 (Nice-to-Have)
- [ ] Async tool registry variant
- [ ] Memory tool metadata filtering
- [ ] Task tool distributed locking
- [ ] Tool versioning + deprecation helpers
- [ ] Observability hooks for latency/frequency

---

## References

- **Nova Agent Source:** `nova/tools/` (now 16 tools)
- **Comparison Frameworks:** Claude Code (Anthropic), LangGraph (LangChain), AutoGen (Microsoft), Swarm (OpenAI), Hermes (Nous Research)
- **Key Paper:** "Dive into Claude Code: Design Space Analysis" (https://arxiv.org/html/2604.14228v1)

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Creating Tools](GUIDE-001-CREATING_TOOLS.md) | Tool development guide |
| [Permissions](GUIDE-008-PERMISSIONS.md) | Permission system reference |
| [Customizing Nova](GUIDE-003-CUSTOMIZING.md) | Full tools and configuration reference |
| [Documentation Index](DOCUMENTATION_INDEX.md) | Full inventory of all docs |
