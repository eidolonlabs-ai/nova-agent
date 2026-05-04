"""Search files tool — grep/regex search across project files.

Essential for coding tasks: find symbols, patterns, or text across
the workspace.
"""

import logging
import re
from pathlib import Path
from typing import Any

from nova.tools.registry import registry

logger = logging.getLogger(__name__)

SEARCH_FILES_SCHEMA = {
    "name": "search_files",
    "description": (
        "Search for a pattern in files within a directory. "
        "Use 'regex' mode for symbol/function/class searches, "
        "'content' mode for plain text. Returns matching file paths and line previews."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "The search pattern (regex or plain text).",
            },
            "path": {
                "type": "string",
                "description": "Directory to search in (default: current directory).",
                "default": ".",
            },
            "mode": {
                "type": "string",
                "enum": ["regex", "content"],
                "description": "Search mode: 'regex' for patterns, 'content' for literal text.",
                "default": "content",
            },
            "file_pattern": {
                "type": "string",
                "description": "Glob pattern to filter files (e.g., '*.py', 'src/**/*.ts').",
                "default": "*",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of matches to return (default: 50).",
                "default": 50,
            },
        },
        "required": ["pattern"],
    },
}

_MAX_RESULTS = 50
_MAX_PREVIEW_CHARS = 120
# Directories to skip by default
_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".mypy_cache",
}


def _search_files(args: dict[str, Any], **kwargs) -> str:
    """Search for a pattern across files."""
    pattern = args.get("pattern", "")
    search_path = Path(args.get("path", ".")).expanduser()
    mode = args.get("mode", "content")
    file_pattern = args.get("file_pattern", "*")
    max_results = min(args.get("max_results", _MAX_RESULTS), 100)

    if not pattern:
        return "Error: No search pattern provided."

    if not search_path.exists():
        return f"Error: Path not found: {search_path}"

    # Compile regex if needed
    if mode == "regex":
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"Error: Invalid regex pattern: {e}"

    matches = []
    total_files = 0
    done = False

    for file_path in search_path.rglob(file_pattern):
        if done:
            break

        if not file_path.is_file():
            continue

        # Skip hidden/binary dirs
        if any(part in _SKIP_DIRS for part in file_path.parts):
            continue

        total_files += 1

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, PermissionError):
            continue

        for line_num, line in enumerate(content.split("\n"), 1):
            if mode == "regex":
                if regex.search(line):
                    preview = line.strip()[:_MAX_PREVIEW_CHARS]
                    matches.append((str(file_path), line_num, preview))
            else:
                if pattern.lower() in line.lower():
                    preview = line.strip()[:_MAX_PREVIEW_CHARS]
                    matches.append((str(file_path), line_num, preview))

            if len(matches) >= max_results:
                done = True
                break

    if not matches:
        return f"No matches found for '{pattern}' (searched {total_files} files)."

    lines = [f"Found {len(matches)} match(es) for '{pattern}' in {total_files} files:\n"]
    for match_path, line_num, preview in matches:
        lines.append(f"  {match_path}:{line_num}: {preview}")

    if len(matches) >= max_results:
        lines.append(f"\n[...limited to {max_results} results, refine your search...]")

    return "\n".join(lines)


registry.register(
    name="search_files",
    toolset="file",
    schema=SEARCH_FILES_SCHEMA,
    handler=_search_files,
    emoji="🔎",
)
