# ADR-001: Sub-Agent Implementation Comparison

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** ADR (Architecture Decision Record)

> Comparison of sub-agent implementations in Hermes-Agent, OpenClaw, and the Nova Agent design that was adopted.

---

## Overview

This document compares how sub-agents are implemented in **Hermes-Agent**, **OpenClaw**, and the proposed **Nova Agent** design.

---

## 1. Spawning Mechanism

### Hermes-Agent

```python
# tools/delegate_tool.py
def delegate_task(tasks: list[dict], ...) -> str:
    """Spawn one or more sub-agents to handle tasks."""
    
    # Supports batch mode (multiple tasks)
    results = []
    for task in tasks:
        subagent = _build_child_agent(parent, task)
        result = _run_single_child(subagent, task, timeout=300)
        results.append(result)
    
    return json.dumps({"results": results})
```

**Characteristics:**
- Batch spawning (multiple tasks in one call)
- ThreadPoolExecutor with configurable concurrency (default 3)
- Hard timeout (300s)
- Nested cost aggregation

### OpenClaw

```typescript
// src/agents/tools/sessions-spawn-tool.ts
async function spawnSubagent(params: SpawnParams): Promise<SpawnResult> {
    // Spawn modes: "run" (ephemeral) or "session" (persistent)
    
    const session = await spawnSubagentDirect({
        task: params.task,
        mode: params.mode,
        context: params.context,  // "isolated" or "fork"
        timeout: params.timeout,
    });
    
    return {
        sessionId: session.id,
        result: session.result,
        ...
    };
}
```

**Characteristics:**
- Single task per spawn (but can spawn multiple in sequence)
- Async/await model
- Configurable timeout (default 60s, max 300s)
- Session-based (persistent or ephemeral)
- Fork context by default

### Nova Agent (Proposed)

```python
# nova/tools/delegate_tool.py
def delegate_task(
    task: str,
    label: str | None = None,
    model: str | None = None,
    timeout_seconds: int = 60,
    context_mode: str = "isolated",
) -> str:
    """Spawn a sub-agent to handle a task."""
    
    result = spawn_subagent(
        task=task,
        parent_agent=parent,
        timeout_seconds=timeout_seconds,
        context_mode=context_mode,
    )
    
    return json.dumps(result)
```

**Characteristics:**
- Single task per call (simple, explicit)
- ThreadPoolExecutor (like Hermes)
- Hard timeout (max 300s)
- Isolated context by default (like Hermes)
- Minimal parameters (task, label, model, timeout, context_mode)

---

## 2. Context Passing

### Hermes-Agent

```python
# Fresh conversation (default)
messages = [
    {"role": "user", "content": task}
]

# No fork mode — sub-agent always starts fresh
# Parent transcript never passed to child
```

**Rationale:**
- Keeps sub-agent focused on task
- Prevents context window bloat
- Simpler implementation

### OpenClaw

```typescript
// Fork mode (default)
const parentTranscript = parent.messages;
const childMessages = [
    ...parentTranscript,
    {"role": "user", "content": task}
];

// Isolated mode (optional)
const childMessages = [
    {"role": "user", "content": task}
];
```

**Rationale:**
- Fork mode allows sub-agent to understand parent context
- Useful for context-aware tasks
- Fallback to isolated if fork unavailable

### Nova Agent (Proposed)

```python
# Isolated mode (default)
messages = [
    {"role": "user", "content": task}
]

# Fork mode (optional)
if context_mode == "fork":
    messages = parent_agent.messages.copy()
    messages.append({"role": "user", "content": task})
```

**Rationale:**
- Isolated by default (like Hermes) — simpler, more focused
- Fork mode available for context-aware tasks (like OpenClaw)
- Explicit choice via parameter

---

## 3. Depth & Role System

### Hermes-Agent

```python
# Depth tracking
_delegate_depth = 0  # Root
_delegate_depth = 1  # Child
_delegate_depth = 2  # Grandchild

# Role determination
max_spawn_depth = 2
is_leaf = _delegate_depth >= max_spawn_depth

# Toolset restriction
if is_leaf:
    remove "delegate_task" from toolset
```

**Characteristics:**
- Explicit depth field
- Depth-based role system
- Configurable max depth (default 2)
- Leaf agents cannot spawn

### OpenClaw

```typescript
// Depth tracking in session store
const spawnDepth = session.metadata.spawnDepth || 0;

// Role determination
const maxSpawnDepth = config.delegation.maxSpawnDepth;
const isLeaf = spawnDepth >= maxSpawnDepth;

// Toolset restriction
if (isLeaf) {
    remove "sessions_spawn" from available tools
}
```

**Characteristics:**
- Depth stored in session metadata
- Depth-based role system
- Configurable max depth (default 2)
- Leaf agents cannot spawn

### Nova Agent (Proposed)

```python
# Depth tracking in config
depth = config.get("_subagent_depth", 0)

# Role determination
max_spawn_depth = config.get("delegation", {}).get("max_spawn_depth", 2)
is_leaf = depth >= max_spawn_depth

# Toolset restriction
if is_leaf:
    remove "delegate_task" from toolset
```

**Characteristics:**
- Depth in config (like Hermes)
- Depth-based role system (like both)
- Configurable max depth (default 2)
- Leaf agents cannot spawn

---

## 4. Budget Tracking

### Hermes-Agent

```python
@dataclass
class IterationBudget:
    total: int
    remaining: int
    
    def check(self) -> bool:
        return self.remaining > 0

# Per-subagent
subagent_budget = IterationBudget(total=50, remaining=50)

# Cost aggregation
parent.iteration_count += subagent.iteration_count
parent.tokens_used += subagent.tokens_used
```

**Characteristics:**
- Iteration-based budget (API calls)
- Per-subagent limit (default 50)
- Simple sum aggregation
- Nested rollup for orchestrators

### OpenClaw

```typescript
// Per-spawn timeout
const timeout = params.timeout || config.defaultTimeout;
const maxTimeout = 300;  // Hard max

// Gateway timeout
const gatewayTimeout = baseTimeout + bufferTime;

// No explicit iteration budget
// Relies on timeout + model's built-in limits
```

**Characteristics:**
- Timeout-based budget (seconds)
- Per-spawn configurable (default 60s, max 300s)
- No explicit iteration limit
- Relies on timeout enforcement

### Nova Agent (Proposed)

```python
@dataclass
class SubAgentBudget:
    system_prompt_tokens: int
    context_tokens: int
    tool_result_tokens: int
    max_iterations: int
    timeout_seconds: int
    
    iterations_used: int = 0
    tokens_used: int = 0

# Per-subagent
subagent_budget = SubAgentBudget(
    max_iterations=30,
    timeout_seconds=60,
    ...
)

# Cost aggregation
parent.iteration_count += subagent.iteration_count
parent.tokens_used += subagent.tokens_used
```

**Characteristics:**
- Explicit token budgets (like Nova's philosophy)
- Iteration + timeout limits
- Per-subagent tracking
- Simple sum aggregation

---

## 5. Thread Model

### Hermes-Agent

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=max_concurrent_children) as executor:
    futures = []
    for task in tasks:
        future = executor.submit(_run_single_child, task)
        futures.append(future)
    
    results = [f.result(timeout=timeout) for f in futures]
```

**Characteristics:**
- ThreadPoolExecutor (synchronous)
- Parallel execution (up to max_concurrent_children)
- Hard timeout per thread
- Main thread waits for all

### OpenClaw

```typescript
// Async/await model
const promises = tasks.map(task => spawnSubagentDirect(task));
const results = await Promise.all(promises);

// Timeout via AbortController
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), timeout);
```

**Characteristics:**
- Async/await (non-blocking)
- Parallel execution (up to max_concurrent_children)
- Timeout via AbortController
- Main thread doesn't block

### Nova Agent (Proposed)

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=1) as executor:
    future = executor.submit(_run_subagent_with_timeout, subagent, task)
    result = future.result(timeout=timeout_seconds)
```

**Characteristics:**
- ThreadPoolExecutor (synchronous, like Hermes)
- Single worker per spawn (simpler)
- Hard timeout per thread
- Main thread waits

---

## 6. Error Handling

### Hermes-Agent

```python
try:
    result = _run_single_child(subagent, task, timeout=300)
except TimeoutError:
    result = {
        "success": False,
        "error": "Sub-agent timed out",
        "timeout": True,
    }
except Exception as e:
    result = {
        "success": False,
        "error": str(e),
        "timeout": False,
    }
```

**Characteristics:**
- Timeout detection
- Exception wrapping
- Result includes error details
- Parent can retry or fall back

### OpenClaw

```typescript
try {
    const result = await spawnSubagentDirect(params);
    return { success: true, result };
} catch (error) {
    if (error.name === "AbortError") {
        return { success: false, timeout: true, error: "Timeout" };
    }
    return { success: false, timeout: false, error: error.message };
}
```

**Characteristics:**
- Timeout detection via AbortError
- Exception wrapping
- Result includes error details
- Parent can retry or fall back

### Nova Agent (Proposed)

```python
try:
    result = future.result(timeout=timeout_seconds)
    return {
        "success": True,
        "result": result,
        "iterations": subagent.iteration_count,
        "tokens_used": subagent.tokens_used,
        "error": None,
        "timeout": False,
    }
except TimeoutError:
    return {
        "success": False,
        "result": None,
        "iterations": subagent.iteration_count,
        "tokens_used": subagent.tokens_used,
        "error": "Sub-agent timed out",
        "timeout": True,
    }
except Exception as e:
    return {
        "success": False,
        "result": None,
        "iterations": subagent.iteration_count,
        "tokens_used": subagent.tokens_used,
        "error": str(e),
        "timeout": False,
    }
```

**Characteristics:**
- Timeout detection
- Exception wrapping
- Result includes error + budget details
- Parent can retry or fall back

---

## 7. Comparison Table

| Aspect | Hermes-Agent | OpenClaw | Nova (Proposed) |
|--------|--------------|----------|-----------------|
| **Spawn** | Batch (multiple tasks) | Single task | Single task |
| **Thread Model** | ThreadPoolExecutor | Async/await | ThreadPoolExecutor |
| **Context** | Isolated (fresh) | Fork (default) | Isolated (default) |
| **Depth Tracking** | `_delegate_depth` | Session metadata | Config field |
| **Role System** | Orchestrator/Leaf | Orchestrator/Leaf | Orchestrator/Leaf |
| **Max Depth** | 2 (default) | 2 (default) | 2 (default) |
| **Budget Type** | Iterations | Timeout | Iterations + Timeout |
| **Timeout** | Hard 300s | Configurable 300s max | Hard 300s max |
| **Concurrency** | 3 (default) | 10 (default) | 3 (default) |
| **Cost Aggregation** | Nested rollup | Per-spawn | Simple sum |
| **Lifecycle Hooks** | Limited | Full | Minimal |
| **Approval Flow** | Auto-deny/approve | Auto-deny/approve | N/A (CLI only) |
| **Blocked Tools** | delegate_task, clarify, memory, send_message, execute_code | sessions_spawn (if leaf) | delegate_task (if leaf) |

---

## 8. Design Rationale for Nova

### Why Isolated Context (not Fork)?

**Hermes-Agent approach:**
- Simpler implementation
- Keeps sub-agent focused
- Prevents context window bloat
- Explicit task boundary

**OpenClaw approach:**
- Sub-agent understands parent context
- Better for context-aware tasks
- More flexible

**Nova choice: Isolated by default, Fork optional**
- Matches Hermes philosophy (simpler, focused)
- Allows Fork mode for context-aware tasks (like OpenClaw)
- Explicit parameter makes intent clear
- Balances simplicity with flexibility

### Why Single Task (not Batch)?

**Hermes-Agent approach:**
- Batch spawning (multiple tasks in one call)
- More efficient for parallel work
- Requires result aggregation logic

**OpenClaw approach:**
- Single task per spawn
- Simpler API
- Parent can spawn multiple in sequence

**Nova choice: Single task**
- Simpler API (fewer parameters)
- Easier to understand and debug
- Parent can spawn multiple if needed
- Matches Nova's minimalist philosophy

### Why ThreadPoolExecutor (not Async)?

**Hermes-Agent approach:**
- ThreadPoolExecutor (synchronous)
- Simpler for Python
- Works with blocking tools (terminal, file I/O)

**OpenClaw approach:**
- Async/await (non-blocking)
- More efficient for I/O
- Requires async tool implementations

**Nova choice: ThreadPoolExecutor**
- Matches Nova's synchronous architecture
- Works with existing blocking tools
- Simpler implementation
- Consistent with Hermes-Agent

### Why Explicit Token Budgets?

**Nova's philosophy:**
- Explicit budgets at every layer
- Predictable costs
- Clear resource constraints

**Implementation:**
- System prompt tokens
- Context tokens
- Tool result tokens
- Max iterations
- Timeout seconds

---

## 9. Implementation Complexity

### Hermes-Agent
- ~2400 lines in `delegate_tool.py`
- Complex batch handling
- Nested cost aggregation
- Approval flow integration

### OpenClaw
- ~1500 lines across multiple files
- Session-based architecture
- Async/await throughout
- Full lifecycle hooks

### Nova (Proposed)
- ~500 lines total
- Single task per spawn
- Simple cost aggregation
- Minimal lifecycle tracking

**Nova is simpler because:**
1. Single task (not batch)
2. Isolated context (not fork)
3. Simple cost sum (not nested rollup)
4. Minimal lifecycle hooks
5. No approval flow (CLI only)

---

## 10. Conclusion

Nova's sub-agent design strikes a balance between **Hermes-Agent's simplicity** and **OpenClaw's flexibility**:

| Dimension | Nova's Choice |
|-----------|---------------|
| **Simplicity** | Single task, isolated context, simple aggregation |
| **Flexibility** | Optional fork mode, configurable timeout, model override |
| **Consistency** | ThreadPoolExecutor (like Hermes), explicit budgets (like Nova) |
| **Minimalism** | ~500 lines, no new dependencies, clear boundaries |

This design can be implemented incrementally and tested thoroughly before shipping.

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [ADR-002: Sub-Agent Design](ADR-002-SUBAGENT_DESIGN.md) | Detailed design spec and implementation plan |
| [Customizing Nova](GUIDE-003-CUSTOMIZING.md) | Delegation configuration reference |
| [Documentation Index](DOCUMENTATION_INDEX.md) | Full inventory of all docs |
