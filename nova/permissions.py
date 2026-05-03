"""Permission system — tool execution approval with defense-in-depth.

Provides a configurable permission checker that evaluates tool calls
through a cascade of checks: sensitive paths, tool deny/allow lists,
path rules, command deny patterns, and permission modes.

Design inspired by OpenHarness's PermissionChecker, simplified for
Nova-Agent's minimalist ethos.
"""

import fnmatch
import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class PermissionMode(StrEnum):
    """Permission modes controlling tool execution behavior."""

    AUTO = "auto"  # Allow all tools without confirmation
    ASK = "ask"    # Ask before mutating tools (default)


@dataclass
class PermissionResult:
    """Result of a permission evaluation."""

    allowed: bool
    requires_confirmation: bool = False
    reason: str = ""


# Built-in sensitive paths that can NEVER be overridden
_SENSITIVE_PATH_PATTERNS: tuple[str, ...] = (
    "*/.ssh/*",
    "*/.ssh",
    "*/.aws/credentials",
    "*/.aws/config",
    "*/.config/gcloud/*",
    "*/.azure/*",
    "*/.gnupg/*",
    "*/.docker/config.json",
    "*/.kube/config",
    "*/.nova/credentials.json",
)

# Commands that are always denied (fnmatch patterns)
_DEFAULT_DENIED_COMMANDS: tuple[str, ...] = (
    "rm -rf /",
    "rm -rf /*",
    "dd if=*",
    ":(){*};:*",  # fork bomb
    "mkfs*",
    "fdisk*",
    "format*",
    "shutdown*",
    "reboot*",
    "halt*",
    "poweroff*",
    "init 0*",
    "init 6*",
)

# Tools that are inherently read-only (never need confirmation)
_READ_ONLY_TOOLS: frozenset[str] = frozenset({
    "read_file",
    "search_files",
    "web_search",
    "skills_list",
    "skill_view",
})

# Tools that mutate state (need confirmation in ask mode)
_MUTATING_TOOLS: frozenset[str] = frozenset({
    "write_file",
    "patch_file",
    "terminal",
    "skill_manage",
    "memory",
    "delegate_task",
})


@dataclass
class PermissionSettings:
    """Configurable permission settings."""

    mode: PermissionMode = PermissionMode.ASK
    denied_tools: set[str] = field(default_factory=set)
    allowed_tools: set[str] = field(default_factory=set)
    denied_commands: list[str] = field(default_factory=lambda: list(_DEFAULT_DENIED_COMMANDS))
    path_rules: list[dict[str, Any]] = field(default_factory=list)  # [{"pattern": "...", "allow": bool}]


class PermissionChecker:
    """Evaluates whether a tool call should be allowed, denied, or require confirmation.

    Uses a defense-in-depth cascade:
    1. Built-in sensitive path protection (cannot be overridden)
    2. Explicit tool deny list
    3. Explicit tool allow list
    4. Path-level rules
    5. Command deny patterns
    6. Permission mode (auto vs ask)
    """

    def __init__(self, settings: PermissionSettings | None = None):
        self.settings = settings or PermissionSettings()

    def evaluate(
        self,
        tool_name: str,
        *,
        is_read_only: bool | None = None,
        file_path: str | None = None,
        command: str | None = None,
    ) -> PermissionResult:
        """Evaluate a tool call through the permission cascade.

        Args:
            tool_name: Name of the tool being called.
            is_read_only: Whether the tool is read-only. If None, inferred from tool name.
            file_path: File path argument (for path rule matching).
            command: Command string (for command deny matching).

        Returns:
            PermissionResult with allowed/requires_confirmation/reason.
        """
        # 1. Built-in sensitive path protection (cannot be overridden)
        if file_path and self._matches_sensitive_path(file_path):
            return PermissionResult(
                allowed=False,
                reason=f"Access denied: sensitive path '{file_path}'",
            )

        # 2. Explicit tool deny list
        if tool_name in self.settings.denied_tools:
            return PermissionResult(
                allowed=False,
                reason=f"Tool '{tool_name}' is explicitly denied",
            )

        # 3. Explicit tool allow list (short-circuit)
        if tool_name in self.settings.allowed_tools:
            return PermissionResult(allowed=True)

        # 4. Path-level rules
        if file_path and self.settings.path_rules:
            path_result = self._check_path_rules(file_path)
            if path_result is not None:
                return path_result

        # 5. Command deny patterns
        if command and self.settings.denied_commands and self._matches_denied_command(command):
            return PermissionResult(
                allowed=False,
                reason=f"Command denied by pattern: '{command[:80]}'",
            )

        # 6. Permission mode
        read_only = is_read_only if is_read_only is not None else tool_name in _READ_ONLY_TOOLS

        if read_only:
            return PermissionResult(allowed=True)

        if self.settings.mode == PermissionMode.AUTO:
            return PermissionResult(allowed=True)

        # ASK mode — mutating tools require confirmation
        return PermissionResult(
            allowed=True,
            requires_confirmation=True,
            reason=f"Tool '{tool_name}' requires confirmation",
        )

    def _matches_sensitive_path(self, path: str) -> bool:
        """Check if a path matches any built-in sensitive pattern."""
        # Check both the path and path with trailing slash for directory matches
        for pattern in _SENSITIVE_PATH_PATTERNS:
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path + "/", pattern):
                return True
        return False

    def _check_path_rules(self, path: str) -> PermissionResult | None:
        """Check path against user-defined path rules. Returns None if no match."""
        for rule in self.settings.path_rules:
            pattern = rule.get("pattern", "")
            allow = rule.get("allow", True)
            if fnmatch.fnmatch(path, pattern):
                if allow:
                    return PermissionResult(allowed=True)
                return PermissionResult(
                    allowed=False,
                    reason=f"Path denied by rule: '{pattern}'",
                )
        return None

    def _matches_denied_command(self, command: str) -> bool:
        """Check if a command matches any deny pattern."""
        cmd_lower = command.lower().strip()
        for pattern in self.settings.denied_commands:
            if fnmatch.fnmatch(cmd_lower, pattern.lower()):
                return True
        return False

    def is_mutating_tool(self, tool_name: str) -> bool:
        """Check if a tool is considered mutating (not read-only)."""
        return tool_name in _MUTATING_TOOLS


def build_permission_checker(config: dict) -> PermissionChecker:
    """Build a PermissionChecker from Nova-Agent config."""
    perm_cfg = config.get("permissions", {})

    mode_str = perm_cfg.get("mode", "ask")
    try:
        mode = PermissionMode(mode_str)
    except ValueError:
        logger.warning("Unknown permission mode '%s', defaulting to 'ask'", mode_str)
        mode = PermissionMode.ASK

    settings = PermissionSettings(
        mode=mode,
        denied_tools=set(perm_cfg.get("denied_tools", [])),
        allowed_tools=set(perm_cfg.get("allowed_tools", [])),
        denied_commands=perm_cfg.get("denied_commands", list(_DEFAULT_DENIED_COMMANDS)),
        path_rules=perm_cfg.get("path_rules", []),
    )

    return PermissionChecker(settings)
