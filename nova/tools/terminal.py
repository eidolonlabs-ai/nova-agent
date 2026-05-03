"""Terminal tool — execute shell commands.

Supports local execution with timeout and output size limits.
"""

import logging
import subprocess
from typing import Any

from nova.tools.registry import registry

logger = logging.getLogger(__name__)

# Destructive commands that should be flagged in logs
_DESTRUCTIVE_PATTERNS = [
    "rm -rf", "rm -r /", "dd if=", "mkfs", "fdisk",
    "curl", "wget", "bash -c", "sh -c", "eval",
    "chmod 777", "chown", "sudo",
]

TERMINAL_SCHEMA = {
    "name": "terminal",
    "description": "Execute a shell command and return its output. Use for system queries, file operations, git commands, and running scripts.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum seconds to wait (default: 60).",
                "default": 60,
            },
            "workdir": {
                "type": "string",
                "description": "Working directory for the command.",
            },
        },
        "required": ["command"],
    },
}

_MAX_OUTPUT_CHARS = 8000
_MAX_COMMAND_LENGTH = 10000


def _truncate_output(output: str, max_chars: int = _MAX_OUTPUT_CHARS) -> str:
    """Truncate output to fit within budget."""
    if len(output) <= max_chars:
        return output
    head = int(max_chars * 0.7)
    tail = int(max_chars * 0.2)
    return f"{output[:head]}\n\n[...{len(output) - head - tail:,} chars truncated...]\n\n{output[-tail:]}"


def _is_destructive(command: str) -> bool:
    """Check if a command matches destructive patterns."""
    cmd_lower = command.lower()
    return any(pattern in cmd_lower for pattern in _DESTRUCTIVE_PATTERNS)


def execute_terminal(args: dict[str, Any], **kwargs) -> str:
    """Execute a terminal command."""
    command = args.get("command", "")
    timeout = args.get("timeout", 60)
    workdir = args.get("workdir")

    if not command:
        return "Error: No command provided."

    # Validate command length
    if len(command) > _MAX_COMMAND_LENGTH:
        return f"Error: Command too long (max {_MAX_COMMAND_LENGTH} chars)."

    # Validate timeout range
    if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 3600:
        return "Error: Timeout must be between 1 and 3600 seconds."

    # Log with destructive flag
    destructive_flag = " [DESTRUCTIVE]" if _is_destructive(command) else ""
    logger.info("Executing%s: %s", destructive_flag, command[:200])

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir,
        )

        output_parts = []
        if result.stdout:
            output_parts.append(_truncate_output(result.stdout))
        if result.stderr:
            output_parts.append(f"stderr:\n{_truncate_output(result.stderr)}")

        output = "\n".join(output_parts) if output_parts else "(no output)"
        return f"exit code: {result.returncode}\n{output}"

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout}s."
    except Exception as e:
        return f"Error: {e}"


registry.register(
    name="terminal",
    toolset="terminal",
    schema=TERMINAL_SCHEMA,
    handler=execute_terminal,
    emoji="💻",
)
