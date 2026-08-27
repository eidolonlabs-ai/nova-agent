# Security Policy

**Status:** ✅ Active  
**Last Updated:** August 2026

---

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | ✅         |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in Nova Agent, please report it responsibly.

### How to Report

**Do NOT open a public issue.** Instead, email us at:

- **Security contact:** security@eidolonlabs.ai

Include as much detail as possible:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### What to Expect

- **Acknowledgment:** Within 48 hours
- **Assessment:** Within 1 week
- **Resolution timeline:** Depends on severity

## Security Considerations

### Prompt Injection Scanning

Nova Agent includes built-in prompt injection scanning for context files. It detects and blocks:
- "Ignore previous instructions" patterns
- "Disregard prior directives" patterns
- Shell command injection attempts (e.g., `curl` exfiltration)

Blocked content is marked with `[BLOCKED: potential prompt injection]` in the system prompt.

### API Key Handling

- API keys are loaded from `config.yaml` or the `LLM_API_KEY` environment variable (`OPENROUTER_API_KEY` also accepted for backward compatibility)
- Keys are never logged or printed to the terminal
- The `config.yaml` file is excluded from git via `.gitignore`

### Terminal Tool

The `terminal` tool executes shell commands with the user's privileges. Be aware:
- Commands run with the same permissions as the Nova process
- No sandboxing is applied — commands can access any file the user can
- Output is truncated to 8,000 characters to prevent context overflow

### File Operations

- `read_file`, `write_file`, and `patch_file` operate with the user's file permissions
- Paths are resolved before access, preventing traversal and symlink escapes outside known workspaces
- Known workspaces are the user's home directory, the system temporary directory, and the current working directory
- Sensitive directories such as `.ssh`, `.aws`, `.gnupg`, `.kube`, and `.docker` are blocked
- Protected system paths such as `/etc`, `/proc`, `/sys`, and `/dev` are blocked
- Workspace restrictions do not sandbox the `terminal` tool, which can access any file the user can access
- `write_file` uses atomic writes (temp file + rename) to prevent corruption

Automatically loaded project-local `config.yaml` files are treated as untrusted preferences. They cannot override
permissions, MCP, or delegation settings, and cannot redirect the LLM endpoint or supply an API key. Use an explicit
config path when those settings are intentionally supplied by a trusted operator.

### Session Data

- Sessions are stored in SQLite at `~/.nova/sessions/sessions.db`
- Contains conversation history, tool calls, and results
- Deleting a session purges its content from the full-text search index (`session_search`, `message_search`)
- No encryption at rest — protect your `~/.nova/` directory

### Memory Data

- Memory is an Obsidian-compatible wiki of Markdown notes under `~/.nova/wiki/`
- Contains user preferences, environment details, project state, and tool quirks
- No encryption at rest — protect your `~/.nova/` directory

### MCP (Model Context Protocol)

- stdio server subprocesses run with a **sanitized environment** — common credential variables (`*KEY*`, `*TOKEN*`, `*SECRET*`, `*PASSWORD*`, `*CREDENTIAL*`) are stripped; secrets a server genuinely needs must be passed explicitly via its `env:` config
- Every stdio request has a 60-second read timeout, so a hung server cannot block the agent loop
- MCP tool/resource results are truncated and labeled as **untrusted external content**
- MCP servers cannot be configured by auto-discovered project-local `config.yaml` files

### Web Tools (Firecrawl)

- `web_parse` uploads local file bytes to Firecrawl and runs the same path-safety checks as `read_file`/`write_file` — sensitive paths (`.ssh`, `.aws`, `.env`, …) and files outside known workspaces are denied
- `web_crawl` and `web_extract` require confirmation in `ask` mode because every page they process costs credits
- All returned web content is labeled as untrusted data

## Best Practices

1. **Never commit `config.yaml`** — it contains your API key
2. **Use environment variables** for API keys in shared environments
3. **Review tool outputs** before executing destructive commands
4. **Keep Nova Agent updated** to receive security patches
5. **Restrict `~/.nova/` directory permissions** if storing sensitive data

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [README](README.md) | Project overview |
| [CONTRIBUTING](CONTRIBUTING.md) | Development and PR guidelines |
| [Permissions](docs/GUIDE-008-PERMISSIONS.md) | Tool permission system reference |
