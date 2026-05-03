# Permission System

Nova Agent includes a configurable permission system that controls tool execution through a defense-in-depth cascade. This prevents accidental or malicious actions while maintaining flexibility.

## Quick Start

Add to your `config.yaml`:

```yaml
permissions:
  mode: "ask"    # "auto" (allow all) or "ask" (confirm mutating tools)
```

## Permission Modes

| Mode | Behavior |
|------|----------|
| `auto` | All tools execute without confirmation (current default behavior) |
| `ask` | Read-only tools execute freely; mutating tools require confirmation |

In CLI mode, `ask` mode logs a confirmation notice but auto-approves (no interactive prompt yet). This is designed for future TUI integration where a real approval dialog would appear.

## Defense-in-Depth Cascade

Every tool call is evaluated through these checks, in order:

1. **Built-in sensitive path protection** — Cannot be overridden. Blocks access to:
   - `~/.ssh/*`, `~/.aws/credentials`, `~/.aws/config`
   - `~/.config/gcloud/*`, `~/.azure/*`, `~/.gnupg/*`
   - `~/.docker/config.json`, `~/.kube/config`
   - `~/.nova/credentials.json`

2. **Explicit tool deny list** — Tools the agent can never use:
   ```yaml
   permissions:
     denied_tools: ["terminal", "write_file"]
   ```

3. **Explicit tool allow list** — Tools that bypass confirmation in `ask` mode:
   ```yaml
   permissions:
     allowed_tools: ["patch_file"]
   ```

4. **Path-level rules** — fnmatch patterns for file access control:
   ```yaml
   permissions:
     path_rules:
       - pattern: "/etc/*"
         allow: false
       - pattern: "/tmp/*"
         allow: true
   ```

5. **Command deny patterns** — Shell commands that are always blocked:
   ```yaml
   permissions:
     denied_commands:
       - "rm -rf /"
       - "rm -rf /*"
       - ":(){*};:*"        # Fork bomb
       - "mkfs*"
       - "shutdown*"
   ```

6. **Permission mode** — Final check based on `auto` vs `ask` mode

## Read-Only vs Mutating Tools

Tools are classified as read-only or mutating:

**Read-only** (never need confirmation):
- `read_file`, `search_files`, `web_search`
- `skills_list`, `skill_view`

**Mutating** (require confirmation in `ask` mode):
- `write_file`, `patch_file`, `terminal`
- `skill_manage`, `memory`, `delegate_task`

## Tool-Level Permission Checking

The terminal tool also checks denied commands independently:

```yaml
permissions:
  denied_commands:
    - "rm -rf /"
    - "curl *"
    - "wget *"
```

File operation tools (`read_file`, `write_file`, `patch_file`) check sensitive paths and path rules.

## Configuration Reference

```yaml
permissions:
  mode: "auto"                    # "auto" or "ask"
  denied_tools: []                # Tools the agent can never use
  allowed_tools: []               # Tools that bypass confirmation
  denied_commands: []             # Shell command patterns (fnmatch)
  path_rules: []                  # Path-level rules
    # - pattern: "/etc/*"
    #   allow: false
```
