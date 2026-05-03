# Nova Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/eidolonlabs-ai/nova-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/eidolonlabs-ai/nova-agent/actions/workflows/ci.yml)

A minimalist personal AI agent with explicit token budgets and smart context management.

By [Eidolon Labs LLC](https://github.com/eidolonlabs-ai).


<img width="1324" height="444" alt="image" src="https://github.com/user-attachments/assets/8e7bfe5d-5b88-4ef4-a587-4a295bcb1aa6" />


<img width="1141" height="626" alt="image" src="https://github.com/user-attachments/assets/98df7b6c-84d8-4fb8-9a42-5af226f2ab16" />


## Design Philosophy

Nova Agent combines the best patterns from two mature agent frameworks:

- **From Hermes-Agent**: Tool registry pattern, skills system, context file discovery, session storage, prompt injection scanning
- **From OpenClaw**: Explicit token budgets, prompt mode gating, head/tail truncation, turn limits, two-tier tool descriptions

## Features

- **Explicit token budgets** at every layer — system prompt, skills, context files, conversation history
- **Smart context management** with head/tail truncation (70/20 ratio) and compression warnings
- **Tool registry** for extensible tools with JSON schema definitions
- **Skills system** with SKILL.md files and starter skills for coding, git, and file editing
- **Context file discovery** (AGENTS.md, SOUL.md, CLAUDE.md, .cursorrules) with injection scanning
- **SQLite session storage** with FTS5 search
- **Prompt mode gating** — full mode for main agent, minimal for sub-agents
- **OpenRouter API** for flexible model selection (100+ models)
- **Streaming responses** with rich terminal UI
- **Simple file-based memory** system with automatic system prompt refresh
- **Web search** via Bing RSS (zero dependencies, zero API key)

## Built-in Tools

| Tool | Description |
|------|-------------|
| `terminal` | Execute shell commands with timeout and output limits |
| `read_file` | Read files with line range support |
| `write_file` | Write/overwrite files with atomic saves |
| `patch_file` | Search/replace patches for targeted edits |
| `search_files` | Grep/regex search across project files |
| `web_search` | Web search via Bing RSS (zero dependencies, zero API key) |
| `skills_list` | List all available skills by category |
| `skill_view` | Load a skill's full instructions |
| `skill_manage` | Create, update, or delete skills |
| `memory` | Add, search, delete, or clear persistent memories |
| `delegate_task` | Spawn a sub-agent to handle an isolated task (opt-in) |

## Installation

### For End Users

**One-line install:**

```bash
curl -fsSL https://raw.githubusercontent.com/eidolonlabs-ai/nova-agent/main/scripts/install.sh | bash
```

This clones Nova to `~/.nova/nova-agent/`, creates a virtual environment, installs dependencies, and adds the `nova` command to your PATH.

**Configure:**

```bash
nova setup
```

The interactive wizard walks you through setting your OpenRouter API key and choosing a model.

**Update:**

```bash
nova update
```

Pulls the latest code and reinstalls dependencies.

---

### For Developers

**Clone and install:**

```bash
git clone https://github.com/eidolonlabs-ai/nova-agent.git
cd nova-agent
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

**Run tests:**

```bash
ruff check . && mypy nova/ && pytest
```

**Run:**

```bash
nova chat
```

Developer installs use the repo's local `.venv` and `config.yaml` in the project root. Changes to source code take effect immediately (editable install).

## Configuration

Nova loads config in layers (later overrides earlier):

1. **Built-in defaults** — sensible fallbacks for everything
2. **`~/.nova/config.yaml`** — global config (API key, model, budgets)
3. **`config.yaml`** in current directory — project-specific overrides

### For End Users

Run the interactive wizard:

```bash
nova setup
```

Or create `~/.nova/config.yaml` manually:

```yaml
openrouter:
  api_key: "sk-or-..."        # or set OPENROUTER_API_KEY env var
  model: "qwen/qwen3.6-flash" # Fast, capable, affordable
```

### For Developers

Copy the example config to the project root:

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` in the repo root. This overrides the global config for this project only.

### Default Files (Recommended)

Copy starter files to your Nova home directory:

```bash
mkdir -p ~/.nova/skills
cp config/SOUL.md.example ~/.nova/SOUL.md
cp -r config/skills/* ~/.nova/skills/
```

See [docs/customizing.md](docs/customizing.md) for the full customization guide.

## Sub-Agent Delegation

Nova supports spawning sub-agents to handle isolated or parallelizable tasks. Sub-agents run in a worker thread with their own context, budget, and timeout.

**Enable in `config.yaml`:**

```yaml
delegation:
  enabled: true
  max_spawn_depth: 2        # root → child → grandchild (leaf)
  default_timeout_seconds: 60
  subagent_budgets:
    max_iterations: 30
```

**How it works:**

1. The root agent (orchestrator) calls `delegate_task(task="...")` as a tool
2. A child `NovaAgent` is spawned in a worker thread with a fresh conversation
3. The child runs with a minimal system prompt (no skills index, no context files) focused on the task
4. Results are returned as JSON and aggregated into the parent's response

**Parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `task` | required | Self-contained task description |
| `label` | auto | Short label for logging |
| `model` | parent's | Override model (e.g. cheaper model for simple tasks) |
| `timeout_seconds` | 60 | Hard timeout (max 300s) |
| `context_mode` | `isolated` | `isolated` (fresh) or `fork` (inherit parent transcript) |

**Depth & roles:**

- **Orchestrator** (depth < `max_spawn_depth`): can call `delegate_task`
- **Leaf** (depth ≥ `max_spawn_depth`): cannot delegate further

Check delegation state with `/status` in the chat UI.

## Usage

```bash
# Interactive chat
nova chat

# One-shot query
nova ask "What's the weather today?"

# Check session history
nova sessions

# Clear current session
nova reset

# Update to latest version (end users)
nova update
```

## Project Structure

```
nova/
  __init__.py
  __main__.py       # Package entry point
  agent.py          # Main agent loop with tool calling & streaming
  cli.py            # CLI entry point (chat, ask, sessions, reset)
  config.py         # YAML config loading with env var resolution
  context.py        # Context file discovery, budgets, truncation
  memory.py         # File-based memory with LRU eviction
  model_metadata.py # Model context window sizes for 20+ models
  prompt.py         # System prompt assembly with mode gating
  session.py        # SQLite session storage with FTS5 search
  skills.py         # Skill discovery, frontmatter parsing, prompt gen
  tokens.py         # Token estimation via tiktoken
  tools/
    __init__.py
    registry.py     # Central tool registry with auto-discovery
    terminal.py     # Shell command execution with timeout
    file_ops.py     # read_file, write_file, patch_file
    search_files.py # Grep/regex search across project files
    web.py          # Bing RSS web search
    skills_tool.py  # skills_list, skill_view, skill_manage
    memory_tool.py  # memory tool (add/search/delete/clear)
    delegate_tool.py # delegate_task sub-agent spawning (opt-in)
config/
  SOUL.md.example   # Agent personality template
  .nova.md.example  # Project instructions template
  skills/           # 3 starter skills
    python-coding/
    git-workflow/
    file-editing/
docs/
  customizing.md    # Comprehensive customization guide
  creating-tools.md # Developer guide: building custom tools
  creating-skills.md # Developer guide: building custom skills
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"
pip install mypy

# Run all checks
ruff check .          # Lint
mypy nova/            # Type check
pytest                # Tests (138 passing)

# Full CI check
ruff check . && mypy nova/ && pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Documentation

| Guide | Description |
|-------|-------------|
| [Customizing Nova](docs/customizing.md) | Config, SOUL.md, context files, memory, sessions |
| [Creating Tools](docs/creating-tools.md) | Build custom tools with schemas, handlers, and tests |
| [Creating Skills](docs/creating-skills.md) | Write effective SKILL.md files for specialized knowledge |

## License

MIT — see [LICENSE](LICENSE) for details.

© 2026 Eidolon Labs LLC

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
For security issues, see [SECURITY.md](SECURITY.md).
