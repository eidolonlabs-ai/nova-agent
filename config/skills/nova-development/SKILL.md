---
name: nova-development
category: development
description: Working on the nova-agent codebase — tool system, permissions, hooks, testing patterns, config, architecture, and CI
---

# Nova Development

## CI Commands

Always use `.venv/bin/` — never global python3 or pytest.

```bash
# Full CI check — must pass before any commit
.venv/bin/ruff check . && .venv/bin/mypy nova/ && .venv/bin/pytest

# Quick smoke (stop on first failure)
.venv/bin/pytest -x -q

# Coverage report
.venv/bin/pytest --cov=nova --cov-report=term-missing

# Single file
.venv/bin/pytest tests/test_tools.py -v
```

## Architecture

```
nova/agent.py          — main agent loop, streaming, tool calling, history truncation
nova/tools/registry.py — central tool registry with auto-discovery
nova/tools/            — individual tool modules (each self-registers at import)
nova/permissions.py    — defense-in-depth permission cascade
nova/hooks.py          — lifecycle event callbacks (pre/post tool/LLM, session)
nova/config.py         — YAML config loading with ${ENV_VAR} resolution, deep merge
nova/prompt.py         — system prompt assembly with mode gating (full/minimal/none)
nova/skills.py         — skill discovery, YAML frontmatter parsing, XML prompt injection
nova/session.py        — SQLite session storage with FTS5 full-text search
nova/memory.py         — file-based memory with LRU eviction
nova/tasks.py          — background task manager (fire-and-forget shell execution)
nova/mcp_client.py     — MCP client: stdio, HTTP, SSE transports
nova/cost_tracker.py   — per-model token usage and dollar cost estimation
nova/compression.py    — LLM-based context compression (Tier 2)
nova/microcompact.py   — cheap context compaction without LLM call (Tier 1)
```

## Tool System

Every tool is a module in `nova/tools/` with three parts: schema, handler, registration.

```python
# nova/tools/my_tool.py
from nova.tools.registry import registry

MY_TOOL_SCHEMA = {
    "name": "my_tool",
    "description": "What it does and when to use it — model reads this to decide whether to call it.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute file path."},
            "limit": {"type": "integer", "description": "Max results (default: 10).", "default": 10},
        },
        "required": ["path"],
    },
}

def _my_tool(args: dict, **kwargs) -> str:
    config = kwargs.get("config", {})
    memory = kwargs.get("memory")   # MemoryStore | None
    agent  = kwargs.get("agent")    # NovaAgent instance
    path   = args.get("path", "")
    limit  = int(args.get("limit", 10))
    # ...
    return "result as string"

registry.register(
    name="my_tool",
    toolset="custom",
    schema=MY_TOOL_SCHEMA,
    handler=_my_tool,
    is_read_only=True,   # omit or False for mutating tools
    emoji="🔧",
)
```

Then add `"nova.tools.my_tool"` to `tool_modules` in `nova/tools/registry.py`.

### Handler rules

- Always return `str` — never `None`, never a dict
- Errors return `"Error: ..."` strings — never raise exceptions
- Large outputs: truncate with head/tail pattern (`head = max_chars * 0.7`, `tail = max_chars * 0.2`)
- Read config via `kwargs.get("config", {})` — never import config at module level
- `is_read_only=True` for tools that never modify state; omit for tools that write or execute

## Testing Patterns

### Testing tool handlers directly

```python
from nova.tools.my_tool import _my_tool

def test_my_tool_basic():
    result = _my_tool({"path": "/tmp/test.txt"}, config={}, memory=None, agent=None)
    assert isinstance(result, str)

def test_my_tool_missing_required_arg():
    result = _my_tool({}, config={}, memory=None, agent=None)
    assert result.startswith("Error:")

def test_my_tool_reads_config():
    config = {"my_tool": {"max_results": 5}}
    result = _my_tool({"path": "/tmp/f.txt"}, config=config, memory=None, agent=None)
    assert result is not None
```

### Testing agent behavior

Inject `http_client`, `session_store`, and `memory_store` — never let tests make real HTTP calls.

```python
from unittest.mock import MagicMock
import httpx
from nova.agent import NovaAgent

def test_agent_something(minimal_config, mock_session_store):
    mock_http = MagicMock(spec=httpx.Client)
    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http,
        session_store=mock_session_store,
        memory_store=None,
    )
    # ... assert agent behavior
```

Use `conftest.py` fixtures (`minimal_config`, `mock_session_store`) — they're already defined.

## Permission System

The agent checks permissions automatically at dispatch. Tools with file paths or commands can also call the checker directly:

```python
from nova.permissions import get_permission_checker

def _my_tool(args: dict, **kwargs) -> str:
    checker = get_permission_checker(kwargs.get("config", {}))
    result = checker.evaluate("my_tool", is_read_only=True, file_path=args.get("path"))
    if not result.allowed:
        return f"Error: Permission denied — {result.reason}"
    # ...
```

Always-blocked paths (cannot be overridden by config):
`~/.ssh/*`, `~/.aws/*`, `~/.gnupg/*`, `~/.docker/config.json`, `~/.kube/config`, `~/.nova/credentials.json`

## Hook System

```python
from nova.hooks import hooks, EVENT_PRE_TOOL_CALL, EVENT_POST_TOOL_CALL, EVENT_POST_LLM_CALL

def my_callback(tool_name: str, args: dict, **kwargs) -> None:
    print(f"[AUDIT] {tool_name}({args})")

hooks.on(EVENT_PRE_TOOL_CALL, my_callback)
hooks.off(EVENT_PRE_TOOL_CALL, my_callback)
```

Events: `pre_tool_call`, `post_tool_call`, `pre_llm_call`, `post_llm_call`, `session_start`

Hooks fire automatically from `registry.dispatch()` — tools don't need to emit them.

## Config System

Add defaults to `DEFAULT_CONFIG` in `nova/config.py`:

```python
DEFAULT_CONFIG = {
    # ...existing...
    "my_feature": {
        "enabled": True,
        "max_items": 10,
    },
}
```

Read in handlers via kwargs:

```python
my_config = kwargs.get("config", {}).get("my_feature", {})
enabled = my_config.get("enabled", True)
```

Users set overrides in `config.yaml`. Use `${ENV_VAR}` syntax for secrets — resolved at load time.

## Skills System

Skills live in `~/.nova/skills/<name>/SKILL.md` with YAML frontmatter. The description is injected into every system prompt — make it specific and searchable (under 100 chars). Starter skills ship in `config/skills/` and are copied with `cp -r config/skills/* ~/.nova/skills/`.

## Common Pitfalls

- Never use global `python3`, `pytest`, or `ruff` — always `.venv/bin/` equivalents
- Never raise exceptions from tool handlers — always return `"Error: ..."` strings
- Never import config at module level in a tool — use `kwargs.get("config", {})`
- Never make real HTTP calls in tests — inject a `MagicMock(spec=httpx.Client)`
- Always add new tools to `tool_modules` in `nova/tools/registry.py`
- Always update `docs/DOCUMENTATION_INDEX.md` when adding docs or skills
- Coverage target is 80%+ for new code — check with `pytest --cov=nova`
