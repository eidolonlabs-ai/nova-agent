# Nova Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/eidolonlabs-ai/nova-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/eidolonlabs-ai/nova-agent/actions/workflows/ci.yml)

A minimalist personal AI agent with explicit token budgets and smart context management.

By [Eidolon Labs LLC](https://github.com/eidolonlabs-ai).

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
- **Web search** via DuckDuckGo (zero dependencies)

## Built-in Tools

| Tool | Description |
|------|-------------|
| `terminal` | Execute shell commands with timeout and output limits |
| `read_file` | Read files with line range support |
| `write_file` | Write/overwrite files with atomic saves |
| `patch_file` | Search/replace patches for targeted edits |
| `search_files` | Grep/regex search across project files |
| `web_search` | Web search via DuckDuckGo HTML (zero dependencies) |
| `skills_list` | List all available skills by category |
| `skill_view` | Load a skill's full instructions |
| `skill_manage` | Create, update, or delete skills |
| `memory` | Add, search, delete, or clear persistent memories |

## Installation

### Quick Install (End Users)

```bash
curl -fsSL https://raw.githubusercontent.com/eidolonlabs-ai/nova-agent/main/scripts/install.sh | bash
```

Then configure your API key:

```bash
nova setup
```

That's it. Nova lives in `~/.nova/nova-agent/` and updates with `nova update`.

### Developer Install

```bash
git clone https://github.com/eidolonlabs-ai/nova-agent.git
cd nova-agent
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

Nova loads config in layers (later overrides earlier):

1. **Built-in defaults** — sensible fallbacks for everything
2. **`~/.nova/config.yaml`** — global config (API key, model, budgets)
3. **`config.yaml`** in current directory — project-specific overrides

### Quick Setup

Run the interactive wizard:

```bash
nova setup
```

Or create `~/.nova/config.yaml` manually:

```yaml
openrouter:
  api_key: "sk-or-..."        # or set OPENROUTER_API_KEY env var
  model: "anthropic/claude-sonnet-4-20250514"
```

### Default Files (Recommended)

Copy starter files to your Nova home directory:

```bash
mkdir -p ~/.nova/skills
cp config/SOUL.md.example ~/.nova/SOUL.md
cp -r config/skills/* ~/.nova/skills/
```

See [docs/customizing.md](docs/customizing.md) for the full customization guide.

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

# Update to latest version
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
    web.py          # DuckDuckGo HTML web search
    skills_tool.py  # skills_list, skill_view, skill_manage
    memory_tool.py  # memory tool (add/search/delete/clear)
config/
  SOUL.md.example   # Agent personality template
  .nova.md.example  # Project instructions template
  skills/           # 3 starter skills
    python-coding/
    git-workflow/
    file-editing/
docs/
  customizing.md    # Comprehensive customization guide
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"
pip install mypy

# Run all checks
ruff check .          # Lint
mypy nova/            # Type check
pytest                # Tests (101 passing)

# Full CI check
ruff check . && mypy nova/ && pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

MIT — see [LICENSE](LICENSE) for details.

© 2026 Eidolon Labs LLC

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
For security issues, see [SECURITY.md](SECURITY.md).
