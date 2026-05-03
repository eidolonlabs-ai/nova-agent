# Nova Agent: Sub-Agent Design Proposal

## Executive Summary

This document proposes a sub-agent architecture for Nova Agent, inspired by patterns from Hermes-Agent and OpenClaw but tailored to Nova's minimalist design philosophy.

**Key principles:**
- Explicit token budgets at every layer (including sub-agents)
- Minimal dependencies — no new external libraries
- Clear parent-child context boundaries
- Depth-based role system (orchestrator vs. leaf)
- Thread-safe execution with hard timeouts

---

## 1. Core Concepts

### 1.1 Sub-Agent Definition

A **sub-agent** is a fresh `NovaAgent` instance spawned by a parent agent to handle a delegated task. Key characteristics:

- **Fresh conversation**: Starts with empty history, task as first user message
- **Isolated context**: No parent transcript by default (can fork on demand)
- **Restricted toolset**: Cannot spawn further sub-agents if at depth limit
- **Separate budget**: Own token budget, iteration limit, timeout
- **Separate task_id**: Prevents file state cache collisions
- **Worker thread**: Runs in ThreadPoolExecutor, not main thread

### 1.2 Depth-Based Role System

```
Depth 0: Root agent (main CLI/gateway entry point)
  ├─ Can spawn sub-agents (depth 1)
  │  ├─ Can spawn sub-agents (depth 2)
  │  │  └─ Cannot spawn (leaf agents)
  │  └─ Cannot spawn if max_spawn_depth=1
  └─ Cannot spawn if max_spawn_depth=0
```

**Roles:**
- **Orchestrator** (depth < max_spawn_depth): Can call `delegate_task` tool
- **Leaf** (depth >= max_spawn_depth): Cannot call `delegate_task` tool

---

## 2. Architecture Overview

### 2.1 File Structure

```
nova/
├── agent.py                    # NovaAgent class (add sub-agent support)
├── tools/
│   ├── registry.py             # Tool registry (unchanged)
│   ├── delegate_tool.py        # NEW: Delegation tool
│   └── ...
├── subagent/                   # NEW: Sub-agent module
│   ├── __init__.py
│   ├── spawn.py                # Spawn logic
│   ├── context.py              # Context passing
│   ├── budget.py               # Budget tracking
│   └── lifecycle.py            # Lifecycle management
└── ...
```

### 2.2 High-Level Flow

```
User Message
    ↓
Parent Agent (depth=0)
    ├─ Identifies task needs delegation
    ├─ Calls delegate_task(task, ...)
    │   ↓
    │   Spawn Sub-Agent (depth=1)
    │   ├─ Fresh conversation
    │   ├─ Task as first message
    │   ├─ Restricted toolset (no delegate_task if depth >= max)
    │   ├─ Own budget/timeout
    │   └─ Runs in worker thread
    │   ↓
    │   Sub-Agent processes task
    │   ├─ Calls tools (terminal, file_ops, etc.)
    │   ├─ Returns result JSON
    │   └─ Cleans up resources
    │   ↓
    ├─ Receives result
    ├─ Aggregates into response
    └─ Returns to user
```

---

## 3. Detailed Design

### 3.1 Delegation Tool Schema

```python
DELEGATE_TASK_SCHEMA = {
    "name": "delegate_task",
    "description": "Spawn a sub-agent to handle a specific task in parallel or sequence.",
    "parameters": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "The task description for the sub-agent.",
            },
            "label": {
                "type": "string",
                "description": "Optional label for this task (for logging/display).",
            },
            "model": {
                "type": "string",
                "description": "Optional model override (e.g., 'gpt-4-turbo'). Defaults to parent's model.",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "Timeout in seconds (default 60, max 300).",
            },
            "context_mode": {
                "type": "string",
                "enum": ["isolated", "fork"],
                "description": "Isolated (fresh) or fork (inherit parent transcript). Default: isolated.",
            },
        },
        "required": ["task"],
    },
}
```

### 3.2 Sub-Agent Configuration

```python
@dataclass
class SubAgentConfig:
    """Configuration for a spawned sub-agent."""
    
    # Identity
    depth: int                          # 0=root, 1+=child
    parent_task_id: str | None          # Parent's task_id for logging
    
    # Execution
    model: str                          # Model to use
    max_iterations: int                 # Iteration limit (default 30)
    timeout_seconds: int                # Hard timeout (default 60, max 300)
    
    # Context
    context_mode: str                   # "isolated" or "fork"
    parent_transcript: list | None      # Parent's messages (if fork mode)
    
    # Budget
    system_prompt_budget: int           # Tokens for system prompt
    context_budget: int                 # Tokens for context files
    tool_result_budget: int             # Tokens per tool result
    
    # Toolset
    enabled_toolsets: list[str] | None  # Inherit from parent if None
    disabled_toolsets: list[str]        # Always disable: delegate_task (if leaf)
```

### 3.3 Sub-Agent Spawning

```python
# nova/subagent/spawn.py

def spawn_subagent(
    task: str,
    parent_agent: NovaAgent,
    label: str | None = None,
    model: str | None = None,
    timeout_seconds: int = 60,
    context_mode: str = "isolated",
) -> dict:
    """Spawn a sub-agent to handle a task.
    
    Returns:
        {
            "success": bool,
            "result": str,              # Task result
            "iterations": int,          # API calls made
            "tokens_used": int,         # Estimated tokens
            "error": str | None,        # Error message if failed
            "timeout": bool,            # True if timed out
        }
    """
    
    # 1. Validate depth
    if parent_agent.depth >= parent_agent.config.get("delegation", {}).get("max_spawn_depth", 2):
        raise ValueError(f"Cannot spawn sub-agent at depth {parent_agent.depth}")
    
    # 2. Build sub-agent config
    subagent_config = _build_subagent_config(
        parent_agent=parent_agent,
        depth=parent_agent.depth + 1,
        model=model or parent_agent.model,
        timeout_seconds=timeout_seconds,
        context_mode=context_mode,
    )
    
    # 3. Create sub-agent instance
    subagent = NovaAgent(
        config=subagent_config,
        http_client=parent_agent.http_client,  # Reuse HTTP client
        session_store=parent_agent.session_store,  # Separate session
        memory_store=parent_agent.memory_store,  # Shared memory
    )
    
    # 4. Run in worker thread with timeout
    result = _run_subagent_with_timeout(
        subagent=subagent,
        task=task,
        timeout_seconds=timeout_seconds,
    )
    
    # 5. Aggregate costs
    parent_agent.iteration_count += result["iterations"]
    parent_agent.tokens_used += result["tokens_used"]
    
    return result
```

### 3.4 Context Passing

**Isolated Mode (default):**
```python
# Sub-agent starts fresh
messages = [
    {"role": "user", "content": task}
]
```

**Fork Mode:**
```python
# Sub-agent inherits parent transcript
messages = parent_agent.messages.copy()
messages.append({"role": "user", "content": task})
```

### 3.5 Toolset Restriction

```python
def _build_subagent_toolset(
    parent_toolset: list[str],
    depth: int,
    max_spawn_depth: int,
) -> list[str]:
    """Build restricted toolset for sub-agent."""
    
    # Start with parent's toolset
    toolset = parent_toolset.copy()
    
    # Remove delegation if at depth limit
    if depth >= max_spawn_depth:
        toolset.remove("delegation")
    
    # Always remove: clarify, memory (to prevent deadlock)
    # (Nova doesn't have these, but pattern for future)
    
    return toolset
```

### 3.6 Budget Tracking

```python
@dataclass
class SubAgentBudget:
    """Per-sub-agent budget tracking."""
    
    system_prompt_tokens: int
    context_tokens: int
    tool_result_tokens: int
    max_iterations: int
    timeout_seconds: int
    
    # Runtime state
    iterations_used: int = 0
    tokens_used: int = 0
    start_time: float = field(default_factory=time.time)
    
    def check_iteration_budget(self) -> bool:
        """Check if iteration budget exceeded."""
        return self.iterations_used >= self.max_iterations
    
    def check_time_budget(self) -> bool:
        """Check if timeout exceeded."""
        elapsed = time.time() - self.start_time
        return elapsed >= self.timeout_seconds
    
    def remaining_time(self) -> float:
        """Seconds remaining before timeout."""
        elapsed = time.time() - self.start_time
        return max(0, self.timeout_seconds - elapsed)
```

### 3.7 Thread-Safe Execution

```python
def _run_subagent_with_timeout(
    subagent: NovaAgent,
    task: str,
    timeout_seconds: int,
) -> dict:
    """Run sub-agent in worker thread with hard timeout."""
    
    from concurrent.futures import ThreadPoolExecutor, TimeoutError
    
    def _worker():
        try:
            response = subagent.chat(task)
            return {
                "success": True,
                "result": response,
                "iterations": subagent.iteration_count,
                "tokens_used": subagent.tokens_used,
                "error": None,
                "timeout": False,
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
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_worker)
        try:
            return future.result(timeout=timeout_seconds)
        except TimeoutError:
            return {
                "success": False,
                "result": None,
                "iterations": subagent.iteration_count,
                "tokens_used": subagent.tokens_used,
                "error": "Sub-agent timed out",
                "timeout": True,
            }
```

---

## 4. Integration Points

### 4.1 NovaAgent Class Changes

```python
class NovaAgent:
    def __init__(self, config: dict, ...):
        # ... existing code ...
        
        # NEW: Sub-agent tracking
        self.depth = config.get("_subagent_depth", 0)
        self.parent_task_id = config.get("_parent_task_id")
        self.is_leaf_agent = self._compute_is_leaf()
    
    def _compute_is_leaf(self) -> bool:
        """Check if this agent can spawn sub-agents."""
        max_depth = self.config.get("delegation", {}).get("max_spawn_depth", 2)
        return self.depth >= max_depth
    
    def chat(self, message: str) -> str:
        """Main chat interface (unchanged)."""
        # ... existing code ...
```

### 4.2 Tool Registry Changes

```python
# nova/tools/registry.py

def _discover_tools(self):
    """Discover and register tools."""
    # ... existing tools ...
    
    # NEW: Register delegation tool
    if not self.is_leaf_agent:
        from nova.tools.delegate_tool import register_delegate_tool
        register_delegate_tool(self)
```

### 4.3 System Prompt Changes

```python
# nova/prompt.py

def build_system_prompt(config: dict, ...) -> str:
    """Build system prompt."""
    parts = []
    
    # ... existing layers ...
    
    # NEW: Delegation guidance (only for orchestrators)
    if not config.get("_is_leaf_agent"):
        parts.append(DELEGATION_GUIDANCE)
    
    return "\n\n".join(parts)

DELEGATION_GUIDANCE = """
## Task Delegation

For complex tasks that can be parallelized or require specialized focus, use the delegate_task tool:
- Provide a clear task description
- Optionally specify a model or timeout
- Use "fork" context mode if the sub-agent needs parent transcript
- Aggregate results into your final response
"""
```

---

## 5. Configuration

### 5.1 config.yaml

```yaml
# Delegation settings
delegation:
  enabled: true
  max_spawn_depth: 2              # Max nesting level
  max_concurrent_children: 3      # Max parallel sub-agents
  default_timeout_seconds: 60     # Default timeout
  max_timeout_seconds: 300        # Hard max timeout
  
  # Sub-agent budgets
  subagent_budgets:
    system_prompt_tokens: 2000
    context_tokens: 5000
    tool_result_tokens: 2000
    max_iterations: 30
```

### 5.2 Environment Variables

```bash
# Optional overrides
NOVA_DELEGATION_ENABLED=true
NOVA_MAX_SPAWN_DEPTH=2
NOVA_SUBAGENT_TIMEOUT=60
```

---

## 6. Example Usage

### 6.1 Simple Delegation

```python
# Parent agent calls delegate_task
response = agent.chat("""
I need to:
1. Analyze this codebase for security issues
2. Generate a report

Please delegate the analysis to a sub-agent.
""")

# Agent internally:
# 1. Identifies need for delegation
# 2. Calls delegate_task("Analyze codebase for security issues")
# 3. Sub-agent runs in parallel
# 4. Parent aggregates result into response
```

### 6.2 Parallel Tasks

```python
# Parent agent spawns multiple sub-agents
response = agent.chat("""
I have 3 independent tasks:
1. Lint the Python code
2. Check TypeScript types
3. Run unit tests

Delegate each to a separate sub-agent and report results.
""")

# Agent internally:
# 1. Calls delegate_task("Lint Python code")
# 2. Calls delegate_task("Check TypeScript types")
# 3. Calls delegate_task("Run unit tests")
# 4. Waits for all to complete (with max_concurrent_children limit)
# 5. Aggregates results
```

### 6.3 Nested Delegation (Orchestrator)

```
User: "Refactor this monolith into microservices"
  ↓
Parent Agent (depth=0, orchestrator)
  ├─ Calls delegate_task("Analyze monolith structure")
  │   ↓
  │   Sub-Agent 1 (depth=1, orchestrator)
  │   ├─ Calls delegate_task("Extract auth module")
  │   │   ↓
  │   │   Sub-Agent 2 (depth=2, leaf) ← Cannot spawn further
  │   │   └─ Returns extracted code
  │   ├─ Calls delegate_task("Extract payment module")
  │   │   ↓
  │   │   Sub-Agent 3 (depth=2, leaf)
  │   │   └─ Returns extracted code
  │   └─ Returns analysis
  ├─ Calls delegate_task("Generate migration plan")
  │   ↓
  │   Sub-Agent 4 (depth=1, orchestrator)
  │   └─ Returns plan
  └─ Aggregates and returns final response
```

---

## 7. Error Handling

### 7.1 Sub-Agent Failures

```python
# If sub-agent fails, parent receives:
{
    "success": False,
    "result": None,
    "error": "Sub-agent encountered an error: ...",
    "timeout": False,
}

# Parent can:
# 1. Retry with different model/timeout
# 2. Fall back to sequential approach
# 3. Report error to user
```

### 7.2 Timeout Handling

```python
# If sub-agent times out:
{
    "success": False,
    "result": None,
    "error": "Sub-agent timed out after 60 seconds",
    "timeout": True,
}

# Parent can:
# 1. Retry with longer timeout
# 2. Simplify task
# 3. Report timeout to user
```

### 7.3 Depth Limit Exceeded

```python
# If leaf agent tries to spawn:
raise ValueError(
    f"Cannot spawn sub-agent at depth {depth}. "
    f"Max spawn depth is {max_spawn_depth}."
)
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# tests/test_subagent_spawn.py
def test_spawn_subagent_basic():
    """Test basic sub-agent spawning."""
    parent = NovaAgent(config)
    result = spawn_subagent("Simple task", parent)
    assert result["success"]
    assert result["result"] is not None

def test_spawn_depth_limit():
    """Test depth limit enforcement."""
    leaf_agent = NovaAgent(config, _subagent_depth=2)
    with pytest.raises(ValueError):
        spawn_subagent("Task", leaf_agent)

def test_subagent_timeout():
    """Test timeout handling."""
    result = spawn_subagent("Infinite loop", parent, timeout_seconds=1)
    assert result["timeout"]
```

### 8.2 Integration Tests

```python
# tests/test_subagent_integration.py
def test_parallel_delegation():
    """Test parallel sub-agent execution."""
    response = agent.chat("Run 3 tasks in parallel")
    assert "completed" in response.lower()

def test_nested_delegation():
    """Test nested sub-agent spawning."""
    response = agent.chat("Delegate to sub-agent, which delegates further")
    assert "depth" in agent.messages[-1]
```

---

## 9. Comparison with Hermes-Agent & OpenClaw

| Aspect | Hermes-Agent | OpenClaw | Nova (Proposed) |
|--------|--------------|----------|-----------------|
| **Spawn mechanism** | `delegate_task` tool | `sessions_spawn` tool | `delegate_task` tool |
| **Context passing** | Fresh (default) | Fork (default) | Fresh (default) |
| **Depth tracking** | `_delegate_depth` | Session store | Config field |
| **Role system** | Orchestrator/Leaf | Orchestrator/Leaf | Orchestrator/Leaf |
| **Toolset restriction** | Yes (blocked list) | Yes (role-based) | Yes (depth-based) |
| **Thread model** | ThreadPoolExecutor | Async/await | ThreadPoolExecutor |
| **Timeout** | Hard (300s) | Configurable (300s max) | Hard (300s max) |
| **Budget tracking** | Per-subagent | Per-spawn | Per-subagent |
| **Concurrency limit** | 3 (default) | 10 (default) | 3 (default) |
| **Lifecycle hooks** | Limited | Full | Minimal (logging only) |
| **Cost aggregation** | Nested rollup | Per-spawn | Simple sum |

---

## 10. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)
- [ ] Create `nova/subagent/` module
- [ ] Implement `spawn_subagent()` function
- [ ] Add depth tracking to `NovaAgent`
- [ ] Implement thread-safe execution with timeout

### Phase 2: Tool Integration (Week 2)
- [ ] Create `delegate_task` tool
- [ ] Register tool in registry
- [ ] Add toolset restriction logic
- [ ] Update system prompt

### Phase 3: Configuration & Testing (Week 3)
- [ ] Add delegation config to `config.yaml.example`
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Test error handling

### Phase 4: Documentation & Polish (Week 4)
- [ ] Update README with delegation examples
- [ ] Add CLI help for `delegate_task`
- [ ] Performance testing
- [ ] Edge case handling

---

## 11. Open Questions

1. **Parallel execution**: Should parent wait for all sub-agents or stream results?
   - Proposal: Wait for all (simpler), with optional streaming in future

2. **Cost aggregation**: Should sub-agent costs count toward parent's budget?
   - Proposal: Yes, simple sum (like Hermes-Agent)

3. **Memory sharing**: Should sub-agents share memory store with parent?
   - Proposal: Yes, but with separate task_id to avoid collisions

4. **Approval flow**: Should sub-agents require approval for sensitive tools?
   - Proposal: No (Nova is CLI-only, no interactive approval needed)

5. **Logging**: How verbose should sub-agent execution be?
   - Proposal: Minimal (log spawn/completion, not every tool call)

---

## 12. Conclusion

This design brings sub-agent support to Nova Agent while maintaining its minimalist philosophy:

- **Explicit budgets** at every layer
- **Minimal dependencies** (no new libraries)
- **Clear boundaries** between parent and child
- **Thread-safe execution** with hard timeouts
- **Inspired by** Hermes-Agent and OpenClaw, but tailored to Nova

The implementation is straightforward, testable, and can be rolled out incrementally.
