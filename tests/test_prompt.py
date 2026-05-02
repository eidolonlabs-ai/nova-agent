"""Tests for system prompt assembly."""

import tempfile
from pathlib import Path

from nova.prompt import (
    DEFAULT_IDENTITY,
    build_system_prompt,
)
from nova.tools.registry import discover_builtin_tools


def _minimal_config() -> dict:
    return {
        "openrouter": {"model": "test-model"},
        "agent": {"identity": "You are a test agent."},
        "budgets": {
            "system_prompt_max": 8000,
            "skills_max_count": 50,
            "skills_max_chars": 15000,
            "context_file_max_chars": 10000,
            "context_total_max_chars": 50000,
        },
        "memory": {"enabled": False},
        "skills": {"enabled": False},
        "context_files": [],
    }


def test_prompt_mode_none():
    """Test that 'none' mode returns only the identity."""
    config = _minimal_config()
    result = build_system_prompt(config, mode="none")
    assert result == "You are a test agent."


def test_prompt_mode_minimal():
    """Test that 'minimal' mode excludes skills and context."""
    config = _minimal_config()
    discover_builtin_tools()
    result = build_system_prompt(config, mode="minimal")

    assert "test agent" in result
    assert "Available Tools" in result
    # Skills and context should NOT appear in minimal mode
    assert "<skills>" not in result
    assert "<context_files>" not in result


def test_prompt_mode_full():
    """Test that 'full' mode includes all layers."""
    config = _minimal_config()
    config["skills"]["enabled"] = True
    config["skills"]["directory"] = str(Path(tempfile.mkdtemp()))
    discover_builtin_tools()

    result = build_system_prompt(config, mode="full")

    assert "test agent" in result
    assert "Available Tools" in result
    assert "Current date:" in result
    assert "Model: test-model" in result


def test_prompt_includes_memory_guidance_when_enabled():
    """Test that memory guidance is included when memory is enabled."""
    config = _minimal_config()
    config["memory"]["enabled"] = True
    discover_builtin_tools()

    result = build_system_prompt(config, mode="minimal")
    assert "Save durable facts" in result or "memory" in result.lower()


def test_prompt_includes_memory_content():
    """Test that prefetched memory content is included."""
    config = _minimal_config()
    config["memory"]["enabled"] = True
    discover_builtin_tools()

    memory_content = "## Memories\n- User prefers Python"
    result = build_system_prompt(config, mode="minimal", memory_content=memory_content)
    assert "User prefers Python" in result


def test_prompt_excludes_memory_guidance_when_disabled():
    """Test that memory guidance is excluded when memory is disabled."""
    config = _minimal_config()
    config["memory"]["enabled"] = False
    discover_builtin_tools()

    result = build_system_prompt(config, mode="minimal")
    assert "Save durable facts" not in result


def test_prompt_budget_enforcement():
    """Test that prompt is truncated when exceeding token budget."""
    config = _minimal_config()
    config["budgets"]["system_prompt_max"] = 50  # Very small budget
    config["memory"]["enabled"] = True
    discover_builtin_tools()

    # Add a lot of memory content
    memory_content = "## Memories\n" + "\n".join(
        f"- Fact number {i}: This is a detailed fact about something."
        for i in range(100)
    )

    result = build_system_prompt(config, mode="minimal", memory_content=memory_content)
    # Should be truncated
    assert "truncated" in result.lower() or len(result) < len(memory_content) + 500


def test_prompt_default_identity():
    """Test that DEFAULT_IDENTITY is used when no custom identity is set."""
    config = _minimal_config()
    del config["agent"]["identity"]
    discover_builtin_tools()

    result = build_system_prompt(config, mode="none")
    assert "Nova" in result
    assert result == DEFAULT_IDENTITY


def test_prompt_tool_summary_format():
    """Test that tool summary is in compact bullet list format."""
    config = _minimal_config()
    discover_builtin_tools()

    result = build_system_prompt(config, mode="minimal")
    # Should contain tool names with emoji bullets
    assert "💻" in result or "terminal" in result
    assert "📖" in result or "read_file" in result


def test_prompt_includes_date_and_model():
    """Test that current date and model info are included."""
    config = _minimal_config()
    discover_builtin_tools()

    result = build_system_prompt(config, mode="minimal")
    assert "Current date:" in result
    assert "Model: test-model" in result
