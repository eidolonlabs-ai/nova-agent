"""Tests for configuration loading."""

import os

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
