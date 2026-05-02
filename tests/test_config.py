"""Tests for configuration loading."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from nova.config import _deep_merge, _resolve_env_vars, load_config


def test_default_config():
    config = load_config()
    assert "openrouter" in config
    assert "agent" in config
    assert "budgets" in config
    assert config["agent"]["max_iterations"] == 50


def test_deep_merge():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"c": 10, "e": 5}}
    result = _deep_merge(base, override)
    assert result["a"] == 1
    assert result["b"]["c"] == 10
    assert result["b"]["d"] == 3
    assert result["b"]["e"] == 5


def test_env_var_resolution():
    os.environ["TEST_NOVA_VAR"] = "resolved_value"
    result = _resolve_env_vars("prefix ${TEST_NOVA_VAR} suffix")
    assert result == "prefix resolved_value suffix"
    del os.environ["TEST_NOVA_VAR"]


def test_env_var_unchanged_if_missing():
    result = _resolve_env_vars("prefix ${NONEXISTENT_VAR_12345} suffix")
    assert result == "prefix ${NONEXISTENT_VAR_12345} suffix"


def test_global_config_loaded():
    """Global config (~/.nova/config.yaml) is loaded when it exists."""
    with tempfile.TemporaryDirectory() as tmp:
        nova_home = Path(tmp) / ".nova"
        nova_home.mkdir()
        config_file = nova_home / "config.yaml"
        config_file.write_text("agent:\n  max_iterations: 99\n")

        with patch("nova.config.get_nova_home", return_value=nova_home):
            config = load_config()
            assert config["agent"]["max_iterations"] == 99


def test_local_config_overrides_global():
    """Local config.yaml overrides values from global config."""
    with tempfile.TemporaryDirectory() as tmp:
        nova_home = Path(tmp) / ".nova"
        nova_home.mkdir()
        global_config = nova_home / "config.yaml"
        global_config.write_text(
            "agent:\n  max_iterations: 99\n  temperature: 0.5\n"
        )

        local_config = Path(tmp) / "config.yaml"
        local_config.write_text("agent:\n  max_iterations: 42\n")

        with patch("nova.config.get_nova_home", return_value=nova_home), \
             patch("pathlib.Path.cwd", return_value=Path(tmp)):
            config = load_config()
            assert config["agent"]["max_iterations"] == 42  # local wins
            assert config["agent"]["temperature"] == 0.5    # from global


def test_no_config_uses_defaults():
    """When no config files exist, defaults are used."""
    with tempfile.TemporaryDirectory() as tmp:
        nova_home = Path(tmp) / ".nova"
        nova_home.mkdir()

        with patch("nova.config.get_nova_home", return_value=nova_home), \
             patch("pathlib.Path.cwd", return_value=Path(tmp)):
            config = load_config()
            assert config["agent"]["max_iterations"] == 50
