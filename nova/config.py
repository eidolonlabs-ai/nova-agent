"""Configuration loading and validation."""

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = {
    "openrouter": {
        "api_key": "",
        "model": "anthropic/claude-sonnet-4-20250514",
        "base_url": "https://openrouter.ai/api/v1",
    },
    "agent": {
        "identity": "You are Nova, a helpful personal assistant.",
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
        "summary_model": "google/gemini-2.0-flash-exp:free",
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
    result = {}
    for key, value in config.items():
        if isinstance(value, dict):
            result[key] = _deep_resolve(value)
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
    """Load configuration from YAML file, falling back to defaults."""
    if config_path is None:
        config_path = Path.cwd() / "config.yaml"

    config = DEFAULT_CONFIG.copy()

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, user_config)

    # Resolve environment variable placeholders
    config = _deep_resolve(config)

    # Ensure API key from env var if not in config
    if not config["openrouter"]["api_key"]:
        config["openrouter"]["api_key"] = os.environ.get("OPENROUTER_API_KEY", "")

    return config


def get_nova_home() -> Path:
    """Get the Nova data directory (~/.nova)."""
    return Path.home() / ".nova"


def ensure_nova_home() -> Path:
    """Ensure the Nova data directory exists."""
    home = get_nova_home()
    home.mkdir(parents=True, exist_ok=True)
    return home
