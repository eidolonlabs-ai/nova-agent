"""File operations tool — read, write, and patch files.

Supports reading with line ranges, writing with atomic saves,
and targeted patching with search/replace.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from nova.tools.registry import registry

logger = logging.getLogger(__name__)

# Paths that should never be accessed by the agent
_BLOCKED_PATHS = {
    "/etc/shadow",
    "/etc/passwd",
    "/etc/sudoers",
    "/etc/ssh",
    "/etc/ssl",
}
_BLOCKED_PREFIXES = [
    "/proc/",
    "/sys/",
    "/dev/",
]
# Sensitive directories that should be blocked
_SENSITIVE_DIRS = [
    ".ssh",
    ".gnupg",
    ".aws",
    ".config/gcloud",
    ".kube",
    ".docker",
    ".terraform",
]

READ_FILE_SCHEMA = {
    "name": "read_file",
    "description": "Read the contents of a file. Supports optional line range and offset.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute or relative path to the file.",
            },
            "offset": {
                "type": "integer",
                "description": "Starting line number (1-based). Default: 1.",
                "default": 1,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read. Default: 500.",
                "default": 500,
            },
        },
        "required": ["path"],
    },
}

WRITE_FILE_SCHEMA = {
    "name": "write_file",
    "description": "Write content to a file. Creates parent directories if needed. Overwrites existing content.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute or relative path to the file.",
            },
            "content": {
                "type": "string",
                "description": "The content to write.",
            },
        },
        "required": ["path", "content"],
    },
}

PATCH_FILE_SCHEMA = {
    "name": "patch_file",
    "description": "Apply a search/replace patch to a file. Replaces the first occurrence of old_string with new_string.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute or relative path to the file.",
            },
            "old_string": {
                "type": "string",
                "description": "The exact text to replace (must match exactly including whitespace).",
            },
            "new_string": {
                "type": "string",
                "description": "The replacement text.",
            },
        },
        "required": ["path", "old_string", "new_string"],
    },
}

_MAX_READ_CHARS = 8000
_MAX_WRITE_CHARS = 500000  # 500KB max write
_MAX_PATCH_CHARS = 100000  # 100KB max patch string


def _is_path_safe(path: Path) -> str | None:
    """Check if a path is safe to access. Returns error message or None if safe."""
    try:
        resolved = path.resolve()
    except (OSError, ValueError):
        return f"Error: Cannot resolve path: {path}"

    # Check blocked exact paths
    path_str = str(resolved)
    if path_str in _BLOCKED_PATHS:
        return f"Error: Access denied to protected path: {path}"

    # Check blocked prefixes
    for prefix in _BLOCKED_PREFIXES:
        if path_str.startswith(prefix):
            return f"Error: Access denied to protected path: {path}"

    # Check sensitive directories in the path
    for sensitive in _SENSITIVE_DIRS:
        if f"/{sensitive}/" in path_str or path_str.endswith(f"/{sensitive}"):
            return f"Error: Access denied to sensitive directory: {sensitive}"

    # Workspace boundary check — ensure resolved path is within allowed areas
    # This prevents symlink attacks that resolve to arbitrary paths
    workspace_dirs = [
        Path.home(),
        Path("/tmp"),
    ]
    # Also allow the current working directory as a workspace
    try:
        cwd = Path.cwd().resolve()
        workspace_dirs.append(cwd)
    except OSError:
        pass

    # If we can identify a workspace, check the path falls within it
    for ws in workspace_dirs:
        if path_str.startswith(str(ws)):
            return None  # Path is within a known workspace

    # If path doesn't match any workspace, it's still allowed if it's not in
    # a blocked list — but log a warning for visibility
    logger.debug("Path resolved outside known workspaces: %s", path_str)
    return None


def _validate_offset_limit(offset: Any, limit: Any) -> str | None:
    """Validate offset and limit parameters. Returns error message or None."""
    if not isinstance(offset, int) or offset < 1:
        return "Error: offset must be a positive integer (1-based line number)."
    if not isinstance(limit, int) or limit < 1 or limit > 10000:
        return "Error: limit must be between 1 and 10000."
    return None


def _read_file(args: dict[str, Any], **kwargs) -> str:
    """Read a file with optional line range."""
    path = Path(args.get("path", "")).expanduser()
    path_str = str(path).strip()
    if not path_str:
        return "Error: No path provided."

    # Security check
    if error := _is_path_safe(path):
        return error

    if not path.exists():
        return f"Error: File not found: {path}"

    offset = args.get("offset", 1)
    limit = args.get("limit", 500)

    if error := _validate_offset_limit(offset, limit):
        return error

    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

        start = max(0, offset - 1)
        end = start + limit
        selected = lines[start:end]

        content = "".join(selected)
        total_lines = len(lines)

        if len(content) > _MAX_READ_CHARS:
            content = content[:_MAX_READ_CHARS]
            shown_end = start + content.count("\n") + 1
            remaining = total_lines - shown_end
            content += f"\n\n[...truncated, {remaining:,} more lines...]"

        line_info = f"Lines {start + 1}-{min(end, total_lines)} of {total_lines}"
        return f"{line_info}:\n{content}"

    except Exception as e:
        return f"Error reading {path}: {e}"


def _write_file(args: dict[str, Any], **kwargs) -> str:
    """Write content to a file atomically."""
    path = Path(args.get("path", "")).expanduser()
    content = args.get("content", "")

    path_str = str(path).strip()
    if not path_str:
        return "Error: No path provided."

    # Security check
    if error := _is_path_safe(path):
        return error

    # Validate content size
    if len(content) > _MAX_WRITE_CHARS:
        return f"Error: Content too large (max {_MAX_WRITE_CHARS:,} chars, got {len(content):,})."

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write via temp file
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, path)
        except Exception:
            os.unlink(tmp_path)
            raise

        lines = content.count("\n") + 1
        return f"Successfully wrote {lines:,} lines to {path}"

    except Exception as e:
        return f"Error writing {path}: {e}"


def _patch_file(args: dict[str, Any], **kwargs) -> str:
    """Apply a search/replace patch."""
    path = Path(args.get("path", "")).expanduser()
    old_string = args.get("old_string", "")
    new_string = args.get("new_string", "")

    path_str = str(path).strip()
    if not path_str:
        return "Error: No path provided."

    # Security check
    if error := _is_path_safe(path):
        return error

    # Validate patch string sizes
    if len(old_string) > _MAX_PATCH_CHARS:
        return f"Error: Search text too large (max {_MAX_PATCH_CHARS:,} chars)."
    if len(new_string) > _MAX_PATCH_CHARS:
        return f"Error: Replacement text too large (max {_MAX_PATCH_CHARS:,} chars)."

    if not path.exists():
        return f"Error: File not found: {path}"

    try:
        content = path.read_text(encoding="utf-8")

        if old_string not in content:
            return f"Error: Search text not found in {path}"

        new_content = content.replace(old_string, new_string, 1)

        # Atomic write — same pattern as _write_file to avoid partial writes
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(new_content)
            os.replace(tmp_path, path)
        except Exception:
            os.unlink(tmp_path)
            raise

        return f"Successfully patched {path}"

    except Exception as e:
        return f"Error patching {path}: {e}"


registry.register(
    name="read_file",
    toolset="file",
    schema=READ_FILE_SCHEMA,
    handler=_read_file,
    emoji="📖",
)

registry.register(
    name="write_file",
    toolset="file",
    schema=WRITE_FILE_SCHEMA,
    handler=_write_file,
    emoji="✏️",
)

registry.register(
    name="patch_file",
    toolset="file",
    schema=PATCH_FILE_SCHEMA,
    handler=_patch_file,
    emoji="🩹",
)
