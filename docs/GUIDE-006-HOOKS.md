# Hook System

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** GUIDE (Feature Reference)

> Nova Agent includes a lightweight hook/callback system for lifecycle events. Enables audit logging, custom tool result transformation, and plugin development without modifying core code.

## Quick Start

Hooks are registered programmatically. Add to your startup script or custom agent wrapper:

```python
from nova.hooks import hooks, EVENT_PRE_TOOL_CALL, EVENT_POST_TOOL_CALL

# Log every tool call
def audit_tool(tool_name, args, **kwargs):
    print(f"[AUDIT] {tool_name} called with args: {args}")

hooks.on(EVENT_PRE_TOOL_CALL, audit_tool)

# Record metrics after tool execution
def record_metric(tool_name, result, **kwargs):
    print(f"[METRIC] {tool_name} returned {len(result)} chars")

hooks.on(EVENT_POST_TOOL_CALL, record_metric)
```

## Available Events

| Event | When it fires | Common kwargs |
|-------|---------------|---------------|
| `pre_tool_call` | Before a tool executes | `tool_name`, `args` |
| `post_tool_call` | After a tool completes | `tool_name`, `args`, `result` |
| `pre_llm_call` | Before calling the LLM API | `messages`, `tools` |
| `post_llm_call` | After LLM responds | `response` |
| `session_start` | When a new session is created | `session_id`, `config` |
| `session_end` | When the agent is closed | *(future)* |

## Hook Registry API

```python
from nova.hooks import hooks

# Register a callback
hooks.on("pre_tool_call", my_callback)

# Remove a callback
hooks.off("pre_tool_call", my_callback)

# Emit an event (called internally by the agent)
hooks.emit("pre_tool_call", tool_name="terminal", args={"command": "ls"})

# Check if any listeners exist
hooks.has_listeners("pre_tool_call")

# Clear callbacks
hooks.clear("pre_tool_call")  # Single event
hooks.clear()                  # All events
```

## Callback Signature

Callbacks receive `**kwargs` specific to the event. They should:

- Accept `**kwargs` to handle any event arguments
- Return any value (collected by the emitter)
- Not raise exceptions (errors are caught and logged)

```python
def my_callback(**kwargs):
    tool_name = kwargs.get("tool_name")
    args = kwargs.get("args", {})
    # Do something...
    return {"status": "ok"}
```

## Use Cases

### Audit Logging

```python
import logging
from nova.hooks import hooks, EVENT_PRE_TOOL_CALL, EVENT_POST_TOOL_CALL

audit_logger = logging.getLogger("nova.audit")

def log_tool_call(tool_name, args, **kwargs):
    audit_logger.info("TOOL_CALL: %s(%s)", tool_name, args)

def log_tool_result(tool_name, result, **kwargs):
    audit_logger.info("TOOL_RESULT: %s → %d chars", tool_name, len(result))

hooks.on(EVENT_PRE_TOOL_CALL, log_tool_call)
hooks.on(EVENT_POST_TOOL_CALL, log_tool_result)
```

### Tool Result Transformation

```python
def sanitize_result(tool_name, result, **kwargs):
    """Remove sensitive data from tool results."""
    if tool_name == "terminal" and "password" in result.lower():
        return "[REDACTED]"
    return result

hooks.on(EVENT_POST_TOOL_CALL, sanitize_result)
```

### Cost Monitoring

```python
from nova.hooks import hooks, EVENT_POST_LLM_CALL

def track_api_calls(response, **kwargs):
    usage = response.get("usage", {})
    print(f"API call: {usage.get('prompt_tokens', 0)} in, "
          f"{usage.get('completion_tokens', 0)} out")

hooks.on(EVENT_POST_LLM_CALL, track_api_calls)
```

## Global vs Instance Hooks

The module provides a global `hooks` singleton:

```python
from nova.hooks import hooks  # Global instance
```

For testing or isolated agents, create a new registry:

```python
from nova.hooks import HookRegistry

my_hooks = HookRegistry()
my_hooks.on("pre_tool_call", my_callback)
```

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Customizing Nova](GUIDE-003-CUSTOMIZING.md) | Full configuration reference |
| [Background Tasks](GUIDE-004-BACKGROUND_TASKS.md) | Use hooks with task lifecycle events |
| [Cost Tracking](GUIDE-005-COST_TRACKING.md) | `EVENT_POST_LLM_CALL` for per-call tracking |
| [Permissions](GUIDE-008-PERMISSIONS.md) | Defense-in-depth before hooks fire |
| [Creating Tools](GUIDE-001-CREATING_TOOLS.md) | Tools that trigger hook events |
