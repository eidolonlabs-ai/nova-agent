"""Configuration loading and validation."""

import copy
import logging
import os
import re
import stat
from pathlib import Path
from typing import Any, cast

import yaml

DEFAULT_CONFIG = {
    "llm": {
        "api_key": "",
        "model": "qwen/qwen3.6-flash",
        "base_url": "https://openrouter.ai/api/v1",
    },
    "web": {
        "firecrawl_api_key": "",
    },
    "agent": {
        "identity": (
            "You are Nova, a capable personal AI agent. "
            "You are direct, efficient, and focused on being genuinely useful. "
            "You take action using tools rather than describing what you would do. "
            "Admit uncertainty when appropriate. Prioritize completing tasks over explaining them."
        ),
        "max_iterations": 50,
        "temperature": 0.7,
        "top_p": 1.0,
    },
    "budgets": {
        "system_prompt_max": 8000,
        "skills_max_chars": 15000,
        "skills_max_count": 50,
        "context_file_max_chars": 10000,
        "context_total_max_chars": 50000,
        "tool_result_max_chars": 8000,
        "tool_result_max_tokens": 3000,
        "conversation_turn_limit": 15,
    },
    "compression": {
        "enabled": True,
        "threshold_percent": 0.40,
        "summary_model": "qwen/qwen3.6-flash",
        "reserve_tokens": 15000,
    },
    "context_files": ["NOVA.md", "AGENTS.md"],
    "wiki": {
        "enabled": True,
        "vault_path": "~/.nova/wiki",
        "max_prompt_notes": 10,
    },
    "skills": {
        "enabled": True,
        "directory": "~/.nova/skills",
    },
    "session": {
        "enabled": True,
        "directory": "~/.nova/sessions",
    },
    "logging": {
        "level": "INFO",
        "file": "~/.nova/nova.log",
    },
    "delegation": {
        "enabled": False,
        "max_spawn_depth": 2,
        "default_timeout_seconds": 60,
        "subagent_budgets": {
            "max_iterations": 30,
            "system_prompt_max": 4000,
            "tool_result_max_chars": 4000,
            "tool_result_max_tokens": 1500,
        },
    },
    "permissions": {
        "mode": "ask",
        "denied_tools": [],
        "allowed_tools": [],
        "denied_commands": [],
        "path_rules": [],
    },
    "mcp": {
        "servers": {},
    },
    "cost_tracking": {
        "enabled": True,
    },
    "microcompact": {
        "enabled": True,
        "keep_recent": 6,
    },
    "tasks": {
        "max_concurrent": 4,
        "max_output_bytes": 100000,
    },
    "retry": {
        "max_retries": 3,
        "base_delay": 1.0,
        "max_delay": 60.0,
    },
}


class ConfigError(ValueError):
    """Raised when configuration values cannot be used safely."""


def _validate_config(config: dict[str, Any]) -> None:
    """Validate resource and model controls before they reach the agent loop."""
    sections = ("llm", "agent", "budgets", "compression", "microcompact", "retry")
    for section in sections:
        if not isinstance(config.get(section), dict):
            raise ConfigError(f"Config section '{section}' must be a mapping")

    agent = config["agent"]
    if not isinstance(agent.get("max_iterations"), int) or not 1 <= agent["max_iterations"] <= 1000:
        raise ConfigError("agent.max_iterations must be an integer between 1 and 1000")
    for name, low, high in (("temperature", 0.0, 2.0), ("top_p", 0.0, 1.0)):
        value = agent.get(name)
        if not isinstance(value, (int, float)) or not low <= value <= high:
            raise ConfigError(f"agent.{name} must be between {low} and {high}")

    budgets = config["budgets"]
    for name, value in budgets.items():
        if not isinstance(value, int) or value < 1:
            raise ConfigError(f"budgets.{name} must be a positive integer")

    compression = config["compression"]
    threshold = compression.get("threshold_percent")
    if not isinstance(threshold, (int, float)) or not 0.05 <= threshold <= 0.95:
        raise ConfigError("compression.threshold_percent must be between 0.05 and 0.95")

    microcompact = config["microcompact"]
    if not isinstance(microcompact.get("keep_recent"), int) or microcompact["keep_recent"] < 0:
        raise ConfigError("microcompact.keep_recent must be a non-negative integer")

    retry = config["retry"]
    if not isinstance(retry.get("max_retries"), int) or not 0 <= retry["max_retries"] <= 10:
        raise ConfigError("retry.max_retries must be between 0 and 10")
    for name in ("base_delay", "max_delay"):
        if not isinstance(retry.get(name), (int, float)) or retry[name] < 0:
            raise ConfigError(f"retry.{name} must be non-negative")

    tasks = config.get("tasks", {})
    if not isinstance(tasks, dict):
        raise ConfigError("Config section 'tasks' must be a mapping")
    if not isinstance(tasks.get("max_concurrent"), int) or not 1 <= tasks["max_concurrent"] <= 32:
        raise ConfigError("tasks.max_concurrent must be an integer between 1 and 32")
    if (
        not isinstance(tasks.get("max_output_bytes"), int)
        or not 1 <= tasks["max_output_bytes"] <= 10_000_000
    ):
        raise ConfigError("tasks.max_output_bytes must be between 1 and 10000000")


def _resolve_env_vars(value: Any) -> Any:
    """Resolve ${ENV_VAR} and $ENV_VAR placeholders in config values."""
    if isinstance(value, str):

        def _replace(match: re.Match) -> str:
            var_name = match.group(1) or match.group(2) or ""
            return os.environ.get(var_name) or match.group(0)

        # Handle both ${VAR} and $VAR forms
        return re.sub(r"\$\{(\w+)\}|\$(\w+)", _replace, value)
    return value


def _deep_resolve(config: dict[str, Any]) -> dict[str, Any]:
    """Recursively resolve env vars in config."""
    result: dict[str, Any] = {}
    for key, value in config.items():
        if isinstance(value, dict):
            result[key] = _deep_resolve(value)  # type: ignore[arg-type]
        else:
            result[key] = _resolve_env_vars(value)
    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


_KNOWN_TOP_LEVEL_KEYS: frozenset[str] = frozenset(DEFAULT_CONFIG.keys()) | frozenset({"openrouter"})
# Internal keys set at runtime (not from user config files)
_RUNTIME_KEYS: frozenset[str] = frozenset({"_subagent_depth"})


def _warn_unknown_keys(user_config: dict[str, Any], source: str) -> None:
    """Warn about unrecognised top-level keys in a user-supplied config."""
    logger = logging.getLogger(__name__)
    unknown = set(user_config.keys()) - _KNOWN_TOP_LEVEL_KEYS - _RUNTIME_KEYS
    for key in sorted(unknown):
        logger.warning("Unknown config key '%s' in %s (typo?)", key, source)


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from YAML files, falling back to defaults.

    Config is loaded in layers (later layers override earlier ones):
    1. DEFAULT_CONFIG (built-in defaults)
    2. ~/.nova/config.yaml (global config, if it exists)
    3. config.yaml in the current directory (local config, if it exists)
    4. Explicit config_path (if provided, overrides local config)
    """
    config = copy.deepcopy(DEFAULT_CONFIG)

    # Layer 2: Global config (~/.nova/config.yaml)
    global_config_path = get_nova_home() / "config.yaml"
    if global_config_path.exists():
        # Check file permissions — warn if world-readable
        file_stat = global_config_path.stat()
        if file_stat.st_mode & (stat.S_IRGRP | stat.S_IROTH):
            logger = logging.getLogger(__name__)
            logger.warning(
                "Config file %s is world-readable. Consider: chmod 600 %s",
                global_config_path,
                global_config_path,
            )
        with open(global_config_path, encoding="utf-8") as f:
            global_config: dict[str, Any] = yaml.safe_load(f) or {}
        _warn_unknown_keys(global_config, str(global_config_path))
        config = _deep_merge(config, global_config)

    # Local config is supported for project preferences, but an untrusted
    # repository must not be able to redirect credentials or tool execution.
    is_automatic_local_config = config_path is None
    resolved_config_path = config_path or (Path.cwd() / "config.yaml")

    if resolved_config_path.exists():
        with open(resolved_config_path, encoding="utf-8") as f:
            user_config: dict[str, Any] = yaml.safe_load(f) or {}
        _warn_unknown_keys(user_config, str(resolved_config_path))
        if is_automatic_local_config:
            user_config = copy.deepcopy(user_config)
            for key in ("permissions", "mcp", "delegation"):
                user_config.pop(key, None)
            if isinstance(user_config.get("llm"), dict):
                user_config["llm"].pop("api_key", None)
                user_config["llm"].pop("base_url", None)
            if isinstance(user_config.get("openrouter"), dict):
                user_config["openrouter"].pop("api_key", None)
                user_config["openrouter"].pop("base_url", None)
            if isinstance(user_config.get("web"), dict):
                user_config["web"].pop("firecrawl_api_key", None)
        config = _deep_merge(config, user_config)

    # Resolve environment variable placeholders
    config = _deep_resolve(config)

    if isinstance(config.get("llm"), dict):
        llm_config = cast(dict[str, Any], config["llm"])
        api_key = llm_config.get("api_key", "")
        if isinstance(api_key, str) and re.fullmatch(r"\$\{?\w+\}?", api_key):
            llm_config["api_key"] = ""

    # Backward compat: migrate old 'openrouter' config key to 'llm'
    if "openrouter" in config:
        old: dict[str, Any] = config.pop("openrouter")  # type: ignore[assignment]
        existing: dict[str, Any] = config.get("llm", {})  # type: ignore[assignment]
        config["llm"] = _deep_merge(existing, old)

    # Ensure API key from env var if not in config
    # Accept LLM_API_KEY (preferred) or OPENROUTER_API_KEY (legacy)
    llm = config.get("llm", {})
    if isinstance(llm, dict) and not llm.get("api_key"):
        config["llm"]["api_key"] = os.environ.get(  # type: ignore[index]
            "LLM_API_KEY", os.environ.get("OPENROUTER_API_KEY", "")
        )

    web = config.get("web")
    if not isinstance(web, dict):
        raise ConfigError("Config section 'web' must be a mapping")
    firecrawl_api_key = web.get("firecrawl_api_key", "")
    if isinstance(firecrawl_api_key, str) and re.fullmatch(r"\$\{?\w+\}?", firecrawl_api_key):
        firecrawl_api_key = ""
    if not firecrawl_api_key:
        web["firecrawl_api_key"] = os.environ.get("FIRECRAWL_API_KEY", "")

    _validate_config(config)
    return config


def get_nova_home() -> Path:
    """Get the Nova data directory (~/.nova)."""
    return Path.home() / ".nova"


def ensure_nova_home() -> Path:
    """Ensure the Nova data directory exists."""
    home = get_nova_home()
    home.mkdir(parents=True, exist_ok=True)
    return home
