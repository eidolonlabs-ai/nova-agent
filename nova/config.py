"""Configuration loading and validation."""

import logging
import os
import stat
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = {
    "openrouter": {
        "api_key": "",
        "model": "qwen/qwen3.6-flash",
        "base_url": "https://openrouter.ai/api/v1",
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
        "conversation_turn_limit": 15,
    },
    "compression": {
        "enabled": True,
        "threshold_percent": 0.40,
        "summary_model": "qwen/qwen3.6-flash",
        "reserve_tokens": 15000,
    },
    "context_files": [".nova.md", "NOVA.md", "AGENTS.md", "SOUL.md", "CLAUDE.md", ".cursorrules"],
    "memory": {
        "enabled": True,
        "max_entries": 100,
        "file": "~/.nova/memory.json",
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
        },
    },
}


def _resolve_env_vars(value: Any) -> Any:
    """Resolve ${ENV_VAR} placeholders in config values."""
    if isinstance(value, str):
        import re

        def _replace(match: re.Match) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))

        return re.sub(r"\$\{(\w+)\}", _replace, value)
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


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from YAML files, falling back to defaults.

    Config is loaded in layers (later layers override earlier ones):
    1. DEFAULT_CONFIG (built-in defaults)
    2. ~/.nova/config.yaml (global config, if it exists)
    3. config.yaml in the current directory (local config, if it exists)
    4. Explicit config_path (if provided, overrides local config)
    """
    config = DEFAULT_CONFIG.copy()

    # Layer 2: Global config (~/.nova/config.yaml)
    global_config_path = get_nova_home() / "config.yaml"
    if global_config_path.exists():
        # Check file permissions — warn if world-readable
        file_stat = global_config_path.stat()
        if file_stat.st_mode & (stat.S_IRGRP | stat.S_IROTH):
            logger = logging.getLogger(__name__)
            logger.warning(
                "Config file %s is world-readable. "
                "Consider: chmod 600 %s",
                global_config_path, global_config_path,
            )
        with open(global_config_path, encoding="utf-8") as f:
            global_config: dict[str, Any] = yaml.safe_load(f) or {}
        config = _deep_merge(config, global_config)

    # Layer 3: Local config (config.yaml in current directory)
    if config_path is None:
        config_path = Path.cwd() / "config.yaml"

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            user_config: dict[str, Any] = yaml.safe_load(f) or {}
        config = _deep_merge(config, user_config)

    # Resolve environment variable placeholders
    config = _deep_resolve(config)

    # Ensure API key from env var if not in config
    openrouter = config.get("openrouter", {})
    if isinstance(openrouter, dict) and not openrouter.get("api_key"):
        config["openrouter"]["api_key"] = os.environ.get("OPENROUTER_API_KEY", "")  # type: ignore[index]

    return config


def get_nova_home() -> Path:
    """Get the Nova data directory (~/.nova)."""
    return Path.home() / ".nova"


def ensure_nova_home() -> Path:
    """Ensure the Nova data directory exists."""
    home = get_nova_home()
    home.mkdir(parents=True, exist_ok=True)
    return home
