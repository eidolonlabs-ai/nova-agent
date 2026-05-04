# Rich Example: README Documentation

> Illustrative README in ai-companions style. Adjust content and paths for your project.

---

# Nova Agent — Minimalist Personal AI

**Status:** ✅ Production ready  
**Latest Release:** v0.1.0  
**Type:** Single-user local agent with explicit token budgets

> Nova is a personal AI agent that runs locally with full control over model selection, API keys, and execution. Designed for developers who want an agentic experience without cloud lock-in.

## Why Nova?

- **Explicit budgets** — Token budgets at every layer (system, skills, tool results)
- **Model agnostic** — OpenRouter-compatible; switch models in config
- **Local first** — No cloud lock-in; your data stays on your machine
- **Skill-based** — Extend with markdown skill files, not code
- **Fast iteration** — 596 passing tests, type-safe Python

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/eidolonlabs-ai/nova-agent.git
cd nova-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Configure
cp config.yaml.example config.yaml
# Edit config.yaml with your OpenRouter API key

# 3. Chat
nova chat
```

## Features

| Feature | Status | Details |
|---------|--------|---------|
| Chat loop | ✅ Active | Streaming responses with history truncation |
| Tool calling | ✅ Active | 10+ built-in tools (terminal, file ops, search, web) |
| Skills system | ✅ Active | Extend with markdown in `~/.nova/skills/` |
| Memory | ✅ Active | File-based LRU store with search |
| Cost tracking | 📋 Planned | Per-conversation token budgets |

## Documentation

| Document | Type | Purpose |
|----------|------|---------|
| [Setup Guide](docs/GUIDE-003-CUSTOMIZING.md) | GUIDE | Installation, configuration, first run |
| [Architecture Decisions](docs/ADR-001-SUBAGENT_COMPARISON.md) | ADR | System design, token budgets, memory |
| [Creating Skills](docs/GUIDE-002-CREATING_SKILLS.md) | GUIDE | Extend with custom knowledge domains |
| [Creating Tools](docs/GUIDE-001-CREATING_TOOLS.md) | GUIDE | Add new tool implementations |
| [Documentation Index](docs/DOCUMENTATION_INDEX.md) | INDEX | Full inventory of all project docs |

## Tests & Quality

- **Test suite:** 596 tests, 75.69% coverage, all passing ✅
- **Type checking:** mypy clean (0 errors in 36 modules)
- **Linting:** ruff compliant
- **CI/CD:** GitHub Actions on every push

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines, code style, and the contribution workflow.

## License

MIT License. See LICENSE file for details.

## Support

- **Issues:** [GitHub Issues](https://github.com/eidolonlabs-ai/nova-agent/issues)
- **Discussions:** [GitHub Discussions](https://github.com/eidolonlabs-ai/nova-agent/discussions)
- **Docs:** [Full Documentation](docs/)
