# Customizing Nova Agent

Nova Agent is designed to be personalized. This guide covers every way you can customize it.

## Quick Start

```bash
# 1. Copy the config
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

Nova uses OpenRouter, giving you access to 100+ models. Change the model in `config.yaml`:

```yaml
openrouter:
  model: "anthropic/claude-sonnet-4-20250514"  # Fast, capable, affordable
  # model: "anthropic/claude-opus-4-20250514"  # Most capable
  # model: "google/gemini-2.5-pro"              # Large context window
  # model: "openai/gpt-4o"                      # Good all-rounder
  # model: "qwen/qwen3.6-flash"                 # Fast and cheap
```

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

Skills are directories containing `SKILL.md` files with YAML frontmatter. They provide specialized knowledge for specific tasks.

### Location

Skills live in `~/.nova/skills/`. Nova discovers them automatically.

### Creating a Skill

```bash
mkdir -p ~/.nova/skills/my-skill
```

Create `~/.nova/skills/my-skill/SKILL.md`:

```markdown
---
name: my-skill
category: general
description: What this skill does in one sentence
---

# My Skill

Detailed instructions, conventions, and workflows go here.
The agent loads this when the skill is relevant.
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Skill identifier (used in `skill_view`) |
| `category` | No | Grouping for the skills index (default: "general") |
| `description` | No | One-line summary shown in the skills index |

### Starter Skills

Nova comes with 3 starter skills. Copy them to your Nova home:

```bash
cp -r config/skills/* ~/.nova/skills/
```

| Skill | Category | Purpose |
|-------|----------|---------|
| `python-coding` | development | Python conventions, testing, venvs |
| `git-workflow` | development | Git branching, committing, pushing |
| `file-editing` | development | Safe file editing patterns |

### How Skills Work

1. Nova shows a compact skills index in the system prompt
2. When a task matches a skill's domain, the agent loads it with `skill_view(name)`
3. The full `SKILL.md` content is injected into the conversation
4. The agent follows the skill's instructions

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

Nova comes with 10 built-in tools:

| Tool | Toolset | Description |
|------|---------|-------------|
| `terminal` | terminal | Execute shell commands with timeout |
| `read_file` | file | Read file contents with line ranges |
| `write_file` | file | Write/overwrite files with atomic saves |
| `patch_file` | file | Search/replace patches for targeted edits |
| `search_files` | file | Grep/regex search across project files |
| `web_search` | web | Web search via DuckDuckGo HTML (zero dependencies) |
| `skills_list` | skills | List all available skills by category |
| `skill_view` | skills | Load a skill's full instructions |
| `skill_manage` | skills | Create, update, or delete skills |
| `memory` | memory | Add, search, delete, or clear persistent memories |

### Adding Custom Tools

Tools are registered in `nova/tools/`. To add a new tool:

1. Create a new file in `nova/tools/my_tool.py`
2. Define a schema and handler
3. Call `registry.register()` at module level

Example:

```python
from nova.tools.registry import registry

MY_TOOL_SCHEMA = {
    "name": "my_tool",
    "description": "What it does",
    "parameters": {
        "type": "object",
        "properties": {
            "arg": {"type": "string", "description": "An argument"},
        },
        "required": ["arg"],
    },
}

def _my_tool(args, **kwargs):
    return f"Result: {args['arg']}"

registry.register(
    name="my_tool",
    toolset="custom",
    schema=MY_TOOL_SCHEMA,
    handler=_my_tool,
    emoji="🔧",
)
```

The tool is automatically discovered and available in the next session.

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
├── memory.json          # Persistent memories (LRU eviction)
├── nova.log             # Log file
├── sessions/
│   └── sessions.db      # SQLite session storage with FTS5
└── skills/
    ├── python-coding/
    │   └── SKILL.md
    ├── git-workflow/
    │   └── SKILL.md
    └── file-editing/
        └── SKILL.md
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key (alternative to config.yaml) |

## Tips

1. **Keep SOUL.md concise** — it's in every API call, so shorter = cheaper
2. **Use skills for workflows** — if you repeat a process, save it as a skill
3. **Use memory for facts** — preferences, environment details, conventions
4. **Use .nova.md for projects** — project-specific instructions that override defaults
5. **Lower budgets for cheaper models** — if using a fast/cheap model, reduce context budgets
