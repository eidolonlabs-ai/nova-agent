# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | ✅         |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in Nova Agent, please report it responsibly.

### How to Report

**Do NOT open a public issue.** Instead, email us at:

- **Security contact:** security@eidolonlabs.com

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

- API keys are loaded from `config.yaml` or the `OPENROUTER_API_KEY` environment variable
- Keys are never logged or printed to the terminal
- The `config.yaml` file is excluded from git via `.gitignore`

### Terminal Tool

The `terminal` tool executes shell commands with the user's privileges. Be aware:
- Commands run with the same permissions as the Nova process
- No sandboxing is applied — commands can access any file the user can
- Output is truncated to 8,000 characters to prevent context overflow

### File Operations

- `read_file`, `write_file`, and `patch_file` operate with the user's file permissions
- No path traversal protection is applied — the agent can read/write any accessible file
- `write_file` uses atomic writes (temp file + rename) to prevent corruption

### Session Data

- Sessions are stored in SQLite at `~/.nova/sessions/sessions.db`
- Contains conversation history, tool calls, and results
- No encryption at rest — protect your `~/.nova/` directory

### Memory Data

- Memories are stored in JSON at `~/.nova/memory.json`
- Contains user preferences, environment details, and tool quirks
- No encryption at rest

## Best Practices

1. **Never commit `config.yaml`** — it contains your API key
2. **Use environment variables** for API keys in shared environments
3. **Review tool outputs** before executing destructive commands
4. **Keep Nova Agent updated** to receive security patches
5. **Restrict `~/.nova/` directory permissions** if storing sensitive data
