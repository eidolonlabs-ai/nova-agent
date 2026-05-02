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


def _read_file(args: dict[str, Any], **kwargs) -> str:
    """Read a file with optional line range."""
    path = Path(args.get("path", "")).expanduser()
    if not path.exists():
        return f"Error: File not found: {path}"

    offset = args.get("offset", 1)
    limit = args.get("limit", 500)

    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

        start = max(0, offset - 1)
        end = start + limit
        selected = lines[start:end]

        content = "".join(selected)
        total_lines = len(lines)

        if len(content) > _MAX_READ_CHARS:
            content = content[:_MAX_READ_CHARS] + f"\n\n[...truncated, {total_lines - offset - limit + 1:,} more lines...]"

        line_info = f"Lines {start + 1}-{min(end, total_lines)} of {total_lines}"
        return f"{line_info}:\n{content}"

    except Exception as e:
        return f"Error reading {path}: {e}"


def _write_file(args: dict[str, Any], **kwargs) -> str:
    """Write content to a file atomically."""
    path = Path(args.get("path", "")).expanduser()
    content = args.get("content", "")

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

    if not path.exists():
        return f"Error: File not found: {path}"

    try:
        content = path.read_text(encoding="utf-8")

        if old_string not in content:
            return f"Error: Search text not found in {path}"

        new_content = content.replace(old_string, new_string, 1)
        path.write_text(new_content, encoding="utf-8")

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
    emoji="🔧",
)
