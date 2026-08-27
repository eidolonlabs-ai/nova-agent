"""Shared path validation for filesystem tools."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROTECTED_PREFIXES = ("/etc", "/private/etc", "/proc", "/sys", "/dev")
_PROTECTED_FILES = {".netrc", ".git-credentials", ".env", ".npmrc"}
_PROTECTED_DIRS = {
    ".ssh",
    ".aws",
    ".gnupg",
    ".azure",
    ".kube",
    ".docker",
    ".terraform",
    ".config/gcloud",
    ".nova",
}


def _configured_workspace(kwargs: dict[str, Any]) -> Path | None:
    workspace = kwargs.get("workspace")
    config = kwargs.get("config")
    if workspace is None and isinstance(config, dict):
        workspace = config.get("workspace")
    if isinstance(workspace, (str, os.PathLike)) and str(workspace).strip():
        try:
            return Path(workspace).expanduser().resolve()
        except (OSError, ValueError):
            return None
    return None


def path_safety_error(path: Path, **kwargs: Any) -> str | None:
    """Return an error when ``path`` is protected or outside its workspace."""
    try:
        resolved = path.expanduser().resolve()
    except (OSError, ValueError):
        return f"Error: Cannot resolve path: {path}"

    if resolved == Path("/") or resolved == Path("/etc"):
        return f"Error: Access denied to protected path: {path}"
    resolved_str = str(resolved)
    if any(
        resolved_str == prefix or resolved_str.startswith(prefix + "/")
        for prefix in _PROTECTED_PREFIXES
    ):
        return f"Error: Access denied to protected path: {path}"

    parts = resolved.parts
    for index, part in enumerate(parts):
        if part in _PROTECTED_DIRS or part in _PROTECTED_FILES or part.startswith(".env"):
            if part == ".nova" and (index + 1 >= len(parts) or parts[index + 1] != "config.yaml"):
                return f"Error: Access denied to sensitive directory: {part}"
            if part != ".nova":
                return f"Error: Access denied to sensitive path: {path}"
        if part == ".config" and index + 1 < len(parts) and parts[index + 1] == "gcloud":
            return f"Error: Access denied to sensitive path: {path}"
    if ".nova" in parts and "config.yaml" in parts[parts.index(".nova") + 1 :]:
        return f"Error: Access denied to sensitive path: {path}"

    configured = _configured_workspace(kwargs)
    workspaces = [configured] if configured else []
    if not configured:
        workspaces.extend(
            (
                Path.cwd().resolve(),
                Path.home().resolve(),
                Path("/tmp").resolve(),
                Path(tempfile.gettempdir()).resolve(),
            )
        )
    for workspace in workspaces:
        if workspace is not None:
            try:
                resolved.relative_to(workspace)
                return None
            except ValueError:
                pass
    logger.warning("Path denied outside known workspaces: %s", resolved)
    return f"Error: Access denied outside known workspaces: {path}"
