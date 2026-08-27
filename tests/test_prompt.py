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
        "llm": {"model": "test-model"},
        "agent": {"identity": "You are a test agent."},
        "budgets": {
            "system_prompt_max": 8000,
            "skills_max_count": 50,
            "skills_max_chars": 15000,
            "context_file_max_chars": 10000,
            "context_total_max_chars": 50000,
        },
        "wiki": {"enabled": False},
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
    assert "Today:" in result
    assert "Model: test-model" in result


def test_prompt_includes_session_retrieval_guidance():
    """Session retrieval guidance is always present when tools are listed."""
    config = _minimal_config()
    discover_builtin_tools()

    result = build_system_prompt(config, mode="full")

    assert "Session Retrieval" in result
    assert "search_sessions" in result
    assert "search_messages" in result
    assert "read_session" in result
    assert "3+ characters" in result


def test_session_retrieval_guidance_not_gated_by_model_family():
    """Claude-family models get the retrieval guidance too.

    The search workflow used to live only inside EXECUTION_DISCIPLINE, which is
    skipped for Claude/Anthropic models by default — leaving them with no
    in-prompt search guidance.
    """
    config = _minimal_config()
    config["llm"]["model"] = "anthropic/claude-sonnet-4"
    discover_builtin_tools()

    result = build_system_prompt(config, mode="full")

    assert "Session Retrieval" in result
    assert "Execution Discipline" not in result  # Claude models skip that block
    assert "search_sessions" in result


def test_prompt_includes_tool_choice_guidance():
    """Tool-choice guidance steers the model to dedicated tools before terminal."""
    config = _minimal_config()
    discover_builtin_tools()

    result = build_system_prompt(config, mode="full")

    assert "Tool Choice" in result
    assert "Use terminal only when no dedicated tool covers the task" in result


def test_prompt_includes_skills_usage_guidance_when_enabled():
    """Skills usage guidance is emitted alongside the skills index."""
    config = _minimal_config()
    config["skills"]["enabled"] = True
    config["skills"]["directory"] = str(Path(tempfile.mkdtemp()))
    discover_builtin_tools()

    result = build_system_prompt(config, mode="full")

    assert "## Skills" in result
    assert "skill_view" in result


def test_prompt_includes_wiki_guidance_when_enabled():
    """Test that wiki guidance is included when wiki is enabled."""
    config = _minimal_config()
    config["wiki"]["enabled"] = True
    discover_builtin_tools()

    result = build_system_prompt(config, mode="minimal")
    assert "Wiki Knowledge Base" in result or "wiki" in result.lower()


def test_prompt_includes_wiki_content():
    """Test that prefetched wiki content is included."""
    config = _minimal_config()
    config["wiki"]["enabled"] = True
    discover_builtin_tools()

    wiki_content = "<wiki_memory>\n- [[People/Mark]]\n</wiki_memory>"
    result = build_system_prompt(config, mode="minimal", wiki_content=wiki_content)
    assert "People/Mark" in result


def test_prompt_excludes_wiki_guidance_when_disabled():
    """Test that wiki guidance is excluded when wiki is disabled."""
    config = _minimal_config()
    config["wiki"]["enabled"] = False
    discover_builtin_tools()

    result = build_system_prompt(config, mode="minimal")
    assert "Wiki Knowledge Base" not in result


def test_prompt_budget_enforcement():
    """Test that prompt is truncated when exceeding token budget."""
    config = _minimal_config()
    config["budgets"]["system_prompt_max"] = 50  # Very small budget
    config["wiki"]["enabled"] = True
    discover_builtin_tools()

    wiki_content = (
        "<wiki_memory>\n"
        + "\n".join(f"- [[Note {i}]] some details" for i in range(100))
        + "\n</wiki_memory>"
    )

    result = build_system_prompt(config, mode="minimal", wiki_content=wiki_content)
    assert "truncated" in result.lower() or len(result) < len(wiki_content) + 500


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
    assert "Today:" in result
    assert "Model: test-model" in result


# ---------------------------------------------------------------------------
# Delegation prompt tests
# ---------------------------------------------------------------------------


def _delegation_config(depth: int = 0, max_spawn_depth: int = 2) -> dict:
    """Config with delegation enabled."""
    config = _minimal_config()
    config["delegation"] = {
        "enabled": True,
        "max_spawn_depth": max_spawn_depth,
    }
    config["_subagent_depth"] = depth
    return config


def test_delegation_guidance_in_orchestrator_prompt():
    """Orchestrator agents (depth < max) should get delegation guidance."""
    config = _delegation_config(depth=0, max_spawn_depth=2)
    discover_builtin_tools(config)

    result = build_system_prompt(config, mode="minimal")
    assert "Task Delegation" in result
    assert "delegate_task" in result


def test_delegation_guidance_absent_when_disabled():
    """Delegation guidance should not appear when delegation is disabled."""
    config = _minimal_config()
    config["delegation"] = {"enabled": False, "max_spawn_depth": 2}
    discover_builtin_tools(config)

    result = build_system_prompt(config, mode="minimal")
    assert "Task Delegation" not in result
    assert "Focused Sub-Agent" not in result


def test_leaf_agent_guidance_in_leaf_prompt():
    """Leaf agents (depth >= max) should get leaf guidance, not orchestrator guidance."""
    config = _delegation_config(depth=2, max_spawn_depth=2)
    discover_builtin_tools(config)

    result = build_system_prompt(config, mode="minimal")
    assert "Focused Sub-Agent" in result
    assert "Task Delegation" not in result


def test_subagent_uses_minimal_prompt_mode():
    """Sub-agents with mode='minimal' should not get skills or context files."""
    config = _delegation_config(depth=1)
    config["skills"]["enabled"] = True
    config["context_files"] = ["NOVA.md"]
    discover_builtin_tools(config)

    result = build_system_prompt(config, mode="minimal")
    assert "<skills>" not in result
    assert "<context_files>" not in result
