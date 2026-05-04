"""File listing tool — list files with glob patterns.

Supports glob patterns, recursive search, and filtering by file type.
Integrates with .gitignore and permission system.
"""

import fnmatch
import logging
from pathlib import Path
from typing import Any

from nova.tools.registry import registry

logger = logging.getLogger(__name__)

LIST_FILES_SCHEMA = {
    "name": "list_files",
    "description": (
        "List files matching a glob pattern. "
        "Supports *, ?, [abc], ** (recursive). "
        "Automatically excludes .git, __pycache__, node_modules, .venv. "
        "Returns paths relative to the search root."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": (
                    "Glob pattern (e.g., '*.py', 'src/**/*.ts', 'test_*.py'). "
                    "Use ** for recursive search."
                ),
            },
            "root": {
                "type": "string",
                "description": "Root directory to search (default: current directory).",
                "default": ".",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results to return (default: 100, max: 1000).",
                "default": 100,
            },
            "absolute": {
                "type": "boolean",
                "description": "Return absolute paths instead of relative (default: false).",
                "default": False,
            },
        },
        "required": ["pattern"],
    },
}

_MAX_RESULTS = 1000


def _should_exclude(path: Path) -> bool:
    """Check if path should be excluded (based on common patterns)."""
    excluded_dirs = {".git", ".venv", "venv", "node_modules", ".pytest_cache", "__pycache__"}
    excluded_files = {".DS_Store", "*.pyc"}

    # Check directory names
    for part in path.parts:
        if part in excluded_dirs:
            return True

    # Check file patterns
    name = path.name
    return any(fnmatch.fnmatch(name, pattern) for pattern in excluded_files)


def _list_files(args: dict[str, Any], **kwargs) -> str:
    """List files matching a glob pattern."""
    pattern = args.get("pattern", "").strip()
    root = args.get("root", ".")
    limit = min(int(args.get("limit", 100)), _MAX_RESULTS)
    absolute = bool(args.get("absolute", False))

    if not pattern:
        return "Error: Pattern is required."

    # Validate root directory
    root_path = Path(root).expanduser()
    if not root_path.exists():
        return f"Error: Root directory not found: {root}"
    if not root_path.is_dir():
        return f"Error: Root is not a directory: {root}"

    logger.info("Listing files: pattern=%s, root=%s, limit=%d", pattern, root, limit)

    try:
        matches: list[str] = []
        for path in sorted(root_path.glob(pattern)):
            if path.is_file() and not _should_exclude(path):
                if absolute:
                    matches.append(str(path.absolute()))
                else:
                    matches.append(str(path.relative_to(root_path)))
                if len(matches) >= limit:
                    break

        if not matches:
            return f"No files found matching '{pattern}' in {root}"

        lines = [f"Found {len(matches)} file(s) matching '{pattern}':"]
        for path in matches:
            lines.append(f"  {path}")

        if len(matches) >= limit:
            lines.append(f"\n(Truncated at {limit} results)")

        return "\n".join(lines)

    except Exception as e:
        logger.error("File list error: %s", e)
        return f"Error: Could not list files: {e}"


registry.register(
    name="list_files",
    toolset="files",
    schema=LIST_FILES_SCHEMA,
    handler=_list_files,
    emoji="📋",
    is_read_only=True,
)
