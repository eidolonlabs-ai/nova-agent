# Customizing Nova Agent

Nova Agent is designed to be personalized. This guide covers every way you can customize it.

## Quick Start

### For End Users

```bash
# 1. Run the setup wizard
nova setup

# 2. Copy default files to your Nova home
mkdir -p ~/.nova/skills
cp -r config/skills/* ~/.nova/skills/
cp config/SOUL.md.example ~/.nova/SOUL.md
```

### For Developers

```bash
# 1. Copy the config to the project root
cp config.yaml.example config.yaml

# 2. Set your API key (or use env var)
export OPENROUTER_API_KEY="sk-or-v1-..."

# 3. Copy default files to your Nova home
mkdir -p ~/.nova/skills
cp -r config/skills/* ~/.nova/skills/
cp config/SOUL.md.example ~/.nova/SOUL.md
```

## Configuration (`config.yaml`)

### Model Selection

Nova uses OpenRouter, giving you access to 100+ models. The default model is **`qwen/qwen3.6-flash`** — fast, capable, and affordable.

Change the model in your config:

```yaml
openrouter:
  model: "qwen/qwen3.6-flash"         # Default — fast and affordable
  # model: "anthropic/claude-sonnet-4-20250514"  # More capable
  # model: "anthropic/claude-opus-4-20250514"    # Most capable
  # model: "google/gemini-2.5-pro"               # Large context window
  # model: "openai/gpt-4.1"                      # Good all-rounder
```

### Summarization Model

When context compression is triggered, Nova uses a separate (cheaper) model for summarization. The default is also **`qwen/qwen3.6-flash`**:

```yaml
compression:
  enabled: true
  threshold_percent: 0.40
  summary_model: "qwen/qwen3.6-flash"  # Cheap model for summarization
  reserve_tokens: 15000
```

You can use a different model here if you prefer — it only runs during compression, so cost impact is minimal.

### Token Budgets

Nova enforces explicit token budgets at every layer. Adjust these based on your needs:

```yaml
budgets:
  system_prompt_max: 8000           # Max tokens for the entire system prompt
  skills_max_chars: 15000           # Max chars for the skills index section
  skills_max_count: 50              # Max number of skills shown in prompt
  context_file_max_chars: 10000     # Max chars per context file (AGENTS.md, etc.)
  context_total_max_chars: 50000    # Max total chars across all context files
  tool_result_max_chars: 8000       # Max chars per tool result returned to the model
  conversation_turn_limit: 15       # Turns before compression triggers
```

**Lower budgets = fewer tokens = cheaper/faster.** Start conservative and increase if the agent needs more context.

### Agent Identity

Customize the agent's personality:

```yaml
agent:
  identity: "You are Nova, a helpful personal assistant."
  max_iterations: 50          # Max tool calls per conversation turn
  temperature: 0.7            # Creativity (0.0 = deterministic, 1.0 = creative)
  top_p: 1.0                  # Nucleus sampling
```

## SOUL.md — Agent Personality

`SOUL.md` in `~/.nova/` defines the agent's identity, tone, and behavior. Nova loads this as the first section of the system prompt.

```bash
# Create your SOUL.md
cp config/SOUL.md.example ~/.nova/SOUL.md
```

Edit it to match your preferences. The agent reads this on every session start.

## .nova.md — Project Instructions

`.nova.md` in your working directory contains project-specific instructions. Nova discovers it automatically when you chat from that directory.

```bash
# Create project instructions
cp config/.nova.md.example /path/to/project/.nova.md
```

**Discovery order** (first found wins):
1. `.nova.md` / `NOVA.md` (walks up to git root)
2. `AGENTS.md` (cwd only)
3. `SOUL.md` (cwd only)
4. `CLAUDE.md` (cwd only)
5. `.cursorrules` (cwd only)

This means Nova works with any project that already has AI agent instructions.

## Skills

Skills are directories containing `SKILL.md` files with YAML frontmatter. They provide specialized knowledge for specific tasks — coding conventions, deployment workflows, API patterns, and more.

Skills live in `~/.nova/skills/`. Nova discovers them automatically at startup.

**→ Full guide: [Creating Skills](creating-skills.md)**

### Starter Skills

Nova ships with 3 starter skills. Copy them to your Nova home:

```bash
cp -r config/skills/* ~/.nova/skills/
```

| Skill | Category | Purpose |
|-------|----------|---------|
| `python-coding` | development | Python conventions, testing, venvs |
| `git-workflow` | development | Git branching, committing, pushing |
| `file-editing` | development | Safe file editing patterns |

## Memory

Nova has a simple file-based memory system for persistent facts.

### Configuration

```yaml
memory:
  enabled: true
  max_entries: 100          # Max memories before LRU eviction
  file: "~/.nova/memory.json"
```

### How the Agent Uses It

The agent can save and recall memories using the `memory` tool:
- `memory(action="add", content="User prefers concise responses")`
- `memory(action="search", query="preferences")`
- `memory(action="delete", id="mem_0001")`
- `memory(action="clear")`

### Memory Guidelines

The agent is instructed to:
- Save **durable facts** (preferences, environment details, tool quirks)
- Write memories as **declarative facts**, not instructions
- **Not save** task progress, session outcomes, or temporary state

## Tools

Nova comes with 16 built-in tools:

| Tool | Toolset | Description |
|------|---------|-------------|
| `terminal` | terminal | Execute shell commands with timeout |
| `read_file` | file | Read file contents with line ranges |
| `write_file` | file | Write/overwrite files with atomic saves |
| `patch_file` | file | Search/replace patches for targeted edits |
| `search_files` | file | Grep/regex search across project files |
| `web_search` | web | Web search via Bing RSS (zero dependencies, zero API key) |
| `skills_list` | skills | List all available skills by category |
| `skill_view` | skills | Load a skill's full instructions |
| `skill_manage` | skills | Create, update, or delete skills |
| `memory` | memory | Add, search, delete, or clear persistent memories |
| `delegate_task` | delegation | Spawn a sub-agent for isolated tasks |
| `task_create` | tasks | Start a background shell command |
| `task_status` | tasks | Check a background task's status |
| `task_output` | tasks | Read the tail of a task's log |
| `task_stop` | tasks | Stop a running background task |
| `task_list` | tasks | List all background tasks |

### Adding Custom Tools

Tools are Python modules in `nova/tools/` that define a JSON schema and a handler function, then self-register via `registry.register()`.

**→ Full guide: [Creating Tools](creating-tools.md)**

Quick example:

```python
# nova/tools/my_tool.py
from nova.tools.registry import registry

MY_TOOL_SCHEMA = {
    "name": "my_tool",
    "description": "What it does and when to use it.",
    "parameters": {
        "type": "object",
        "properties": {
            "arg": {"type": "string", "description": "An argument"},
        },
        "required": ["arg"],
    },
}


def _my_tool(args: dict, **kwargs) -> str:
    return f"Result: {args['arg']}"


registry.register(
    name="my_tool",
    toolset="custom",
    schema=MY_TOOL_SCHEMA,
    handler=_my_tool,
    emoji="🔧",
)
```

Then add `"nova.tools.my_tool"` to the `tool_modules` list in `nova/tools/registry.py`. The tool is available on the next session start.

## Session Management

Sessions are stored in SQLite at `~/.nova/sessions/sessions.db` with FTS5 full-text search.

```bash
# List recent sessions
nova sessions

# List with custom limit
nova sessions --limit 10

# Start fresh session
nova chat

# Ask a one-shot question
nova ask "What is the capital of France?"

# Reset (clear) a session
nova reset --session <session-id>
```

## Data Directory Structure

```
~/.nova/
├── SOUL.md              # Agent personality (optional)
├── .nova.md             # Project instructions (per-project)
├── config.yaml          # Global configuration
├── memory.json          # Persistent memories (LRU eviction)
├── nova.log             # Log file
├── sessions/
│   └── sessions.db      # SQLite session storage with FTS5
├── skills/
│   ├── python-coding/
│   │   └── SKILL.md
│   ├── git-workflow/
│   │   └── SKILL.md
│   └── file-editing/
│       └── SKILL.md
└── tasks/               # Background task logs
    └── b3f8a2c.log
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key (alternative to config.yaml) |
| `GITHUB_TOKEN` | GitHub personal access token (for MCP GitHub server) |

## Permissions

Nova includes a configurable permission system with defense-in-depth protection.

**→ Full guide: [Permissions](permissions.md)**

Quick config:

```yaml
permissions:
  mode: "auto"                    # "auto" (allow all) or "ask" (confirm mutating tools)
  denied_tools: []                # Tools the agent can never use
  denied_commands:                # Shell commands that are always blocked
    - "rm -rf /"
    - ":(){*};:*"                 # Fork bomb
  path_rules: []                  # Path-level allow/deny rules
```

## Hooks

Register callbacks for lifecycle events like pre/post tool calls, LLM calls, and session start/end.

**→ Full guide: [Hooks](hooks.md)**

Quick example:

```python
from nova.hooks import hooks, EVENT_PRE_TOOL_CALL

def audit(tool_name, args, **kwargs):
    print(f"[AUDIT] {tool_name}({args})")

hooks.on(EVENT_PRE_TOOL_CALL, audit)
```

## Background Tasks

Run long-running commands without blocking the conversation.

**→ Full guide: [Background Tasks](background-tasks.md)**

Use the built-in tools in chat:
- `task_create("command", "description")` — start a background task
- `task_status("task_id")` — check status
- `task_output("task_id")` — read output
- `task_stop("task_id")` — stop a task
- `task_list()` — list all tasks

## MCP Integration

Connect to external Model Context Protocol servers for additional tools.

**→ Full guide: [MCP Integration](mcp-integration.md)**

Quick config:

```yaml
mcp:
  servers:
    filesystem:
      command: npx
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
```

## Cost Tracking

Track token usage and estimated dollar costs per session.

**→ Full guide: [Cost Tracking](cost-tracking.md)**

View with `/usage` in chat:
```
Context used: 12,450 / 128,000 tokens (9%)
Tokens: 45,230 total (32,100 in, 13,130 out) | Cost: $0.002145
```

Disable in config:
```yaml
cost_tracking:
  enabled: false
```

## Context Compression

Nova uses a two-tier compaction strategy to manage context windows:

**Tier 1: Microcompact** — Strips old tool result content while preserving message structure. Cheap, no LLM call needed.

**Tier 2: LLM Summarization** — When microcompact isn't enough, Nova calls a summarization model to condense older messages into a summary, preserving recent context and tool call structure.

```yaml
compression:
  enabled: true
  threshold_percent: 0.40       # Compress at 40% of context window
  summary_model: "qwen/qwen3.6-flash"  # Model for summarization
  reserve_tokens: 15000         # Reserve for compaction overhead

microcompact:
  enabled: true                 # Enable Tier 1 (cheap, no LLM call)
  keep_recent: 6                # Recent messages to preserve fully
```

The compression flow is:
1. Check if total tokens exceed threshold (context_window × threshold_percent - reserve_tokens)
2. **Tier 1**: Strip old tool content → if still over threshold →
3. **Tier 2**: LLM summarizes older messages, injects summary as system message

## Retry Logic

Nova automatically retries failed API calls with exponential backoff and jitter:

```yaml
retry:
  max_retries: 3                # Max retry attempts for transient errors
  base_delay: 1.0               # Initial delay in seconds
  max_delay: 60.0               # Maximum delay cap in seconds
```

**Error classification:**
- **Retryable**: 429 (rate limit), 5xx (server errors), timeout, connection errors
- **Non-retryable**: 4xx (bad request, auth errors) — raised immediately
- **Context overflow**: Triggers compression instead of retry

## Tips

1. **Keep SOUL.md concise** — it's in every API call, so shorter = cheaper
2. **Use skills for workflows** — if you repeat a process, save it as a skill
3. **Use memory for facts** — preferences, environment details, conventions
4. **Use .nova.md for projects** — project-specific instructions that override defaults
5. **Lower budgets for cheaper models** — if using a fast/cheap model, reduce context budgets
6. **Use `permissions.mode: "ask"`** — for safer tool execution (future TUI will show approval dialogs)
7. **Use background tasks** — for long-running commands like test suites or builds
8. **Connect MCP servers** — for filesystem, GitHub, database, and other external tool access
9. **Use a cheap model for `summary_model`** — compression runs frequently, so cost matters
10. **Increase `max_retries` for rate-limited models** — if you hit 429s often, more retries help
