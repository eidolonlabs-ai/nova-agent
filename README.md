# Nova Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

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
| `web_search` | Web search via DuckDuckGo HTML |
| `skills_list` | List all available skills |
| `skill_view` | Load a skill's full instructions |
| `skill_manage` | Create, update, or delete skills |
| `memory` | Add, search, delete, or clear persistent memories |

## Installation

```bash
pip install -e .
```

## Configuration

Copy the example config and edit:

```bash
cp config.yaml.example config.yaml
```

Set your OpenRouter API key and preferred model.

### Default Files (Recommended)

Copy the starter files to your Nova home directory:

```bash
mkdir -p ~/.nova/skills
cp config/SOUL.md.example ~/.nova/SOUL.md
cp -r config/skills/* ~/.nova/skills/
```

See [docs/customizing.md](docs/customizing.md) for the full customization guide.

## Usage

```bash
# Activate the virtual environment
source .venv/bin/activate

# Interactive chat
nova chat

# One-shot query
nova ask "What's the weather today?"

# Check session history
nova sessions

# Clear current session
nova reset
```

## Project Structure

```
nova/
  __init__.py
  agent.py          # Main agent loop
  config.py         # Configuration loading
  context.py        # Context file discovery, budgets, truncation
  memory.py         # Simple memory system
  prompt.py         # System prompt assembly
  session.py        # SQLite session storage
  skills.py         # Skill discovery and loading
  tokens.py         # Token estimation utilities
  tools/
    __init__.py
    registry.py     # Tool registry
    terminal.py     # Shell command execution
    file_ops.py     # File read/write/patch tools
    search_files.py # Grep/regex search across files
    web.py          # Web search (DuckDuckGo)
    skills_tool.py  # Skills list/view/manage
    memory_tool.py  # Memory add/search/delete/clear
  cli.py            # CLI entry point
config/
  SOUL.md.example   # Agent personality template
  .nova.md.example  # Project instructions template
  skills/           # Starter skills
    python-coding/
    git-workflow/
    file-editing/
docs/
  customizing.md    # Comprehensive customization guide
```

## License

MIT — see [LICENSE](LICENSE) for details.

© 2026 Eidolon Labs LLC
