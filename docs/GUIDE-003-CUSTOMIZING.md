# Customizing Nova Agent

**Status:** ✅ Active  
**Last Updated:** May 2026  
**Type:** GUIDE (Comprehensive Reference)

> Nova Agent is designed to be personalized. This guide covers every way you can customize it.

---

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
export LLM_API_KEY="sk-..."

# 3. Copy default files to your Nova home
mkdir -p ~/.nova/skills
cp -r config/skills/* ~/.nova/skills/
cp config/SOUL.md.example ~/.nova/SOUL.md
```

## Configuration (`config.yaml`)

### Model Selection

Nova works with any OpenAI-compatible API — OpenRouter, DeepSeek, OpenAI, Ollama, and others. The default model is **`qwen/qwen3.6-flash`** via OpenRouter — fast, capable, and affordable.

Change the model in your config:

```yaml
llm:
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

`SOUL.md` in `~/.nova/` defines the agent's identity, tone, and behavior. Nova loads this as the first section of the system prompt before any project context.

```bash
# Create your SOUL.md
cp config/SOUL.md.example ~/.nova/SOUL.md
```

Edit it to match your preferences. The agent reads this on every session start, so your personality is always consistent.

## Project Context Files

Nova discovers project-specific instructions in your working directory:

```bash
# Create project config
cp config/NOVA.md.example /path/to/project/NOVA.md

# Create project agent instructions
cp config/AGENTS.md.example /path/to/project/AGENTS.md
```

**Discovery order** (searches up to git root):
1. `NOVA.md` — Project configuration and high-level instructions
2. `AGENTS.md` — Agent-specific behaviors and constraints for the project

Nova walks up the directory tree from your current working directory to the git root, loading the first matching file. This means Nova works automatically with any project that has these files.

## Skills

Skills are directories containing `SKILL.md` files with YAML frontmatter. They provide specialized knowledge for specific tasks — coding conventions, deployment workflows, API patterns, and more.

Skills live in `~/.nova/skills/`. Nova discovers them automatically at startup.

**→ Full guide: [Creating Skills](GUIDE-002-CREATING_SKILLS.md)**

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

## Memory (Wiki)

Nova's memory is an Obsidian-compatible wiki of markdown notes. See [GUIDE-013-MEMORY_SYSTEM](GUIDE-013-MEMORY_SYSTEM.md) for full details on the `Core/` auto-inject convention, maintenance, and best practices.

### Configuration

```yaml
wiki:
  enabled: true                  # On by default
  vault_path: "~/.nova/wiki"     # Or point at an existing Obsidian vault
  max_prompt_notes: 10           # How many recent notes appear in the index
```

### How the Agent Uses It

The agent saves and recalls knowledge using the `wiki` tool:
- `wiki(action="write", title="Core/Preferences", content="Prefers concise responses")`
- `wiki(action="append", title="Projects/nova", content="Added new feature X")`
- `wiki(action="search", query="preferences")`
- `wiki(action="read", title="People/Mark")`
- `wiki(action="list", tag="python")`
- `wiki(action="maintenance")` — read-only report of duplicates, orphans, stale notes
- `wiki(action="delete", title="Old Note")`

### Folder Conventions

- `Core/<topic>` — full content auto-injected into every prompt (keep short!)
- `People/<Name>`, `Projects/<name>`, `Facts/<topic>`, `Concepts/<name>` — searchable reference

### Memory Guidelines

The agent is instructed to:
- **Search first** before writing — avoid duplicates
- Save user preferences and identity to `Core/` for always-in-context recall
- Use `[[wikilinks]]` and `#tags` to connect notes
- Update existing notes when info changes; never create dated snapshots
- Run `wiki maintenance` periodically; never auto-delete without user confirmation

## Tools

Nova comes with 16 built-in tools:

| Tool | Toolset | Status | Description |
|------|---------|--------|-------------|
| `terminal` | terminal | ✅ Active | Execute shell commands with timeout |
| `read_file` | file | ✅ Active | Read file contents with line ranges |
| `write_file` | file | ✅ Active | Write/overwrite files with atomic saves |
| `patch_file` | file | ✅ Active | Search/replace patches for targeted edits |
| `search_files` | file | ✅ Active | Grep/regex search across project files |
| `web_search` | web | ✅ Active | Web search via Bing RSS (zero dependencies) |
| `skills_list` | skills | ✅ Active | List all available skills by category |
| `skill_view` | skills | ✅ Active | Load a skill's full instructions |
| `skill_manage` | skills | ✅ Active | Create, update, or delete skills |
| `wiki` | wiki | ✅ Active | Manage Obsidian-compatible wiki notes: write, append, read, search, list, delete, maintenance |
| `delegate_task` | delegation | ✅ Active | Spawn a sub-agent for isolated tasks |
| `task_create` | tasks | ✅ Active | Start a background shell command |
| `task_status` | tasks | ✅ Active | Check a background task's status |
| `task_output` | tasks | ✅ Active | Read the tail of a task's log |
| `task_stop` | tasks | ✅ Active | Stop a running background task |
| `task_list` | tasks | ✅ Active | List all background tasks |

### Adding Custom Tools

Tools are Python modules in `nova/tools/` that define a JSON schema and a handler function, then self-register via `registry.register()`.

**→ Full guide: [Creating Tools](GUIDE-001-CREATING_TOOLS.md)**

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
├── SOUL.md              # Global agent personality
├── config.yaml          # Global configuration
├── wiki/                # Obsidian-compatible wiki memory
│   ├── Core/            # Always-in-context notes (full content injected)
│   ├── People/          # Notes about users / collaborators
│   ├── Projects/        # Project state, decisions, conventions
│   ├── Facts/           # Durable technical knowledge
│   └── Concepts/        # Definitions and mental models
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

# Project-level (in your project directory)
NOVA.md                 # Project configuration (optional)
AGENTS.md               # Agent instructions (optional)
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `LLM_API_KEY` | Your API key (alternative to config.yaml); `OPENROUTER_API_KEY` also accepted for backward compatibility |
| `GITHUB_TOKEN` | GitHub personal access token (for MCP GitHub server) |

## Permissions

Nova includes a configurable permission system with defense-in-depth protection.

**→ Full guide: [Permissions](GUIDE-008-PERMISSIONS.md)**

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

**→ Full guide: [Hooks](GUIDE-006-HOOKS.md)**

Quick example:

```python
from nova.hooks import hooks, EVENT_PRE_TOOL_CALL

def audit(tool_name, args, **kwargs):
    print(f"[AUDIT] {tool_name}({args})")

hooks.on(EVENT_PRE_TOOL_CALL, audit)
```

## Background Tasks

Run long-running commands without blocking the conversation.

**→ Full guide: [Background Tasks](GUIDE-004-BACKGROUND_TASKS.md)**

Use the built-in tools in chat:
- `task_create("command", "description")` — start a background task
- `task_status("task_id")` — check status
- `task_output("task_id")` — read output
- `task_stop("task_id")` — stop a task
- `task_list()` — list all tasks

## MCP Integration

Connect to external Model Context Protocol servers for additional tools.

**→ Full guide: [MCP Integration](GUIDE-007-MCP_INTEGRATION.md)**

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

**→ Full guide: [Cost Tracking](GUIDE-005-COST_TRACKING.md)**

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

Nova uses a three-tier compaction strategy to manage context windows. See [GUIDE-011-CONTEXT_COMPRESSION](GUIDE-011-CONTEXT_COMPRESSION.md) for the full strategy, trade-offs, and configuration reference.

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
4. **Tier 3**: User runs `/new` to start a fresh session (manual reset)

## Retry Logic

Nova automatically retries failed API calls with exponential backoff and jitter. See [GUIDE-014-RETRY_AND_ERROR_HANDLING](GUIDE-014-RETRY_AND_ERROR_HANDLING.md) for error classification, retry algorithm, and configuration reference.

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
2. **Use NOVA.md for project settings** — project-specific instructions that override defaults
3. **Use AGENTS.md for agent behaviors** — agent constraints and specific workflows
4. **Use skills for workflows** — if you repeat a process, save it as a skill
5. **Use the wiki for facts** — preferences and identity go in `Core/`; reference knowledge elsewhere
6. **Lower budgets for cheaper models** — if using a fast/cheap model, reduce context budgets
7. **Use `permissions.mode: "ask"`** — for safer tool execution (future TUI will show approval dialogs)
8. **Use background tasks** — for long-running commands like test suites or builds
9. **Connect MCP servers** — for filesystem, GitHub, database, and other external tool access
10. **Use a cheap model for `summary_model`** — compression runs frequently, so cost matters
11. **Increase `max_retries` for rate-limited models** — if you hit 429s often, more retries help

---

## Related Documentation

| Document | Type | Purpose |
|----------|------|---------|
| [Creating Skills](GUIDE-002-CREATING_SKILLS.md) | GUIDE | Write and manage SKILL.md files |
| [Creating Tools](GUIDE-001-CREATING_TOOLS.md) | GUIDE | Add custom tool implementations |
| [Permissions](GUIDE-008-PERMISSIONS.md) | GUIDE | Configure the permission system |
| [Hooks](GUIDE-006-HOOKS.md) | GUIDE | Lifecycle callbacks and event system |
| [Background Tasks](GUIDE-004-BACKGROUND_TASKS.md) | GUIDE | Fire-and-forget task execution |
| [MCP Integration](GUIDE-007-MCP_INTEGRATION.md) | GUIDE | Connect to external MCP servers |
| [Cost Tracking](GUIDE-005-COST_TRACKING.md) | GUIDE | Token usage and dollar cost tracking |
| [Roadmap](GUIDE-010-ROADMAP.md) | GUIDE | Project phases, timeline, and targets |
| [Context Compression](GUIDE-011-CONTEXT_COMPRESSION.md) | GUIDE | Three-tier context management strategy |
| [Session Management](GUIDE-012-SESSION_MANAGEMENT.md) | GUIDE | SQLite sessions, FTS5 search, slash commands |
| [Memory System](GUIDE-013-MEMORY_SYSTEM.md) | GUIDE | Obsidian-compatible wiki memory, `Core/` auto-inject, maintenance |
| [Retry & Error Handling](GUIDE-014-RETRY_AND_ERROR_HANDLING.md) | GUIDE | Exponential backoff, error classification |
