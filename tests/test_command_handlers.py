"""Tests for slash command handlers."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nova.command_handlers import (
    _HANDLERS,
    dispatch_command,
    get_registered_commands,
)
from nova.memory import MemoryStore

# ─── Helpers ─────────────────────────────────────────────────────────────────

DISPLAY_MOD = "nova.command_handlers"


def _patch_display():
    """Suppress all terminal output in command handlers."""
    return patch(f"{DISPLAY_MOD}._cprint" if hasattr(__import__("nova.command_handlers", fromlist=[""]), "_cprint") else "nova.display._cprint")


# ─── Registry ────────────────────────────────────────────────────────────────


def test_all_expected_commands_are_registered():
    expected = {"new", "reset", "history", "status", "st", "sessions", "model",
                "tools", "usage", "undo", "compact", "copy", "memory"}
    for cmd in expected:
        assert cmd in _HANDLERS, f"Command '{cmd}' missing from registry"


def test_dispatch_command_returns_true_for_known_command(agent):
    with patch("nova.display._cprint"):
        result = dispatch_command("status", agent, "")
    assert result is True


def test_dispatch_command_returns_false_for_unknown_command(agent):
    result = dispatch_command("nonexistent_xyz", agent, "")
    assert result is False


def test_dispatch_command_handles_handler_exception(agent):
    with patch.dict(_HANDLERS, {"boom": MagicMock(side_effect=RuntimeError("oops"))}):
        with patch("nova.display._cprint"):
            result = dispatch_command("boom", agent, "")
    assert result is True  # handler found, exception caught internally


def test_get_registered_commands_returns_set(agent):
    cmds = get_registered_commands()
    assert isinstance(cmds, set)
    assert len(cmds) > 0


# ─── cmd_new ─────────────────────────────────────────────────────────────────


def test_cmd_new_creates_new_session(agent):
    old_session_id = agent.session_id
    with patch("nova.display._cprint"):
        dispatch_command("new", agent, "")
    assert agent.session_id is not None
    assert agent.session_id != old_session_id


def test_cmd_reset_alias_works(agent):
    old_session_id = agent.session_id
    with patch("nova.display._cprint"):
        dispatch_command("reset", agent, "")
    assert agent.session_id != old_session_id


# ─── cmd_history ─────────────────────────────────────────────────────────────


def test_cmd_history_empty_messages(agent):
    agent.messages = []
    with patch("nova.display._cprint") as mock_print:
        dispatch_command("history", agent, "")
    mock_print.assert_not_called()


def test_cmd_history_shows_user_and_assistant_messages(agent):
    agent.messages = [
        {"role": "user", "content": "hello world"},
        {"role": "assistant", "content": "hi there"},
    ]
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("history", agent, "")
    combined = "\n".join(printed)
    assert "hello world" in combined
    assert "hi there" in combined


def test_cmd_history_truncates_long_assistant_content(agent):
    long_content = "x" * 300
    agent.messages = [{"role": "assistant", "content": long_content}]
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("history", agent, "")
    combined = "\n".join(printed)
    assert "…" in combined


def test_cmd_history_skips_tool_messages(agent):
    agent.messages = [
        {"role": "tool", "content": "tool result"},
    ]
    with patch("nova.display._cprint") as mock_print:
        dispatch_command("history", agent, "")
    mock_print.assert_not_called()


# ─── cmd_status ──────────────────────────────────────────────────────────────


def test_cmd_status_prints_session_info(agent):
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("status", agent, "")
    combined = "\n".join(printed)
    assert agent.session_id in combined
    assert "test-model" in combined


def test_cmd_status_shows_delegation_disabled(agent):
    agent.config.pop("delegation", None)
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("status", agent, "")
    assert any("disabled" in s for s in printed)


def test_cmd_status_shows_delegation_enabled(make_agent, delegation_config):
    a = make_agent(config=delegation_config)
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("status", a, "")
    assert any("enabled" in s for s in printed)


def test_cmd_st_alias_works(agent):
    with patch("nova.display._cprint"):
        result = dispatch_command("st", agent, "")
    assert result is True


# ─── cmd_sessions ─────────────────────────────────────────────────────────────


def test_cmd_sessions_no_sessions(agent):
    agent.session_store.list_sessions = MagicMock(return_value=[])
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("sessions", agent, "")
    assert any("No sessions" in s for s in printed)


def test_cmd_sessions_lists_sessions(agent):
    agent.session_store.list_sessions = MagicMock(return_value=[
        {"id": "abc-123", "created_at": "2026-01-01"},
    ])
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("sessions", agent, "")
    assert any("abc-123" in s for s in printed)


# ─── cmd_model ───────────────────────────────────────────────────────────────


def test_cmd_model_no_args_prints_current_model(agent):
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("model", agent, "")
    assert any("test-model" in s for s in printed)


def test_cmd_model_with_args_switches_model(agent):
    with patch("nova.display._cprint"):
        dispatch_command("model", agent, "openai/gpt-4o")
    assert agent.config["openrouter"]["model"] == "openai/gpt-4o"


def test_cmd_model_trims_whitespace(agent):
    with patch("nova.display._cprint"):
        dispatch_command("model", agent, "  openai/gpt-4o  ")
    assert agent.config["openrouter"]["model"] == "openai/gpt-4o"


# ─── cmd_tools ───────────────────────────────────────────────────────────────


def test_cmd_tools_lists_available_tools(agent):
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("tools", agent, "")
    assert any("Available tools" in s for s in printed)


def test_cmd_tools_prints_tool_names(agent):
    from nova.tools.registry import discover_builtin_tools
    discover_builtin_tools()
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("tools", agent, "")
    assert len(printed) > 1  # header + at least one tool entry


# ─── cmd_usage ───────────────────────────────────────────────────────────────


def test_cmd_usage_without_cost_tracker(agent):
    agent.cost_tracker = None
    with patch("nova.display._cprint") as mock_print:
        dispatch_command("usage", agent, "")
    mock_print.assert_called()


def test_cmd_usage_with_cost_tracker(agent):
    mock_tracker = MagicMock()
    mock_tracker.format_summary.return_value = "Total cost: $0.01"
    agent.cost_tracker = mock_tracker
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("usage", agent, "")
    assert any("$0.01" in s for s in printed)


# ─── cmd_undo ────────────────────────────────────────────────────────────────


def test_cmd_undo_removes_last_exchange(agent):
    agent.messages = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "response"},
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "response2"},
    ]
    with patch("nova.display._cprint"):
        dispatch_command("undo", agent, "")
    assert len(agent.messages) == 2
    assert agent.messages[-1]["content"] == "response"


def test_cmd_undo_does_nothing_when_empty(agent):
    agent.messages = []
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("undo", agent, "")
    assert any("Nothing to undo" in s for s in printed)


def test_cmd_undo_does_nothing_with_one_message(agent):
    agent.messages = [{"role": "user", "content": "only one"}]
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("undo", agent, "")
    assert len(agent.messages) == 1
    assert any("Nothing to undo" in s for s in printed)


# ─── cmd_compact ─────────────────────────────────────────────────────────────


def test_cmd_compact_trims_to_last_four_messages(agent):
    agent.messages = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
    with patch("nova.display._cprint"):
        dispatch_command("compact", agent, "")
    assert len(agent.messages) == 4


def test_cmd_compact_leaves_short_history_unchanged(agent):
    agent.messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    with patch("nova.display._cprint"):
        dispatch_command("compact", agent, "")
    assert len(agent.messages) == 2


# ─── cmd_copy ────────────────────────────────────────────────────────────────


def test_cmd_copy_copies_last_assistant_message(agent):
    agent.messages = [
        {"role": "user", "content": "tell me something"},
        {"role": "assistant", "content": "something interesting"},
    ]
    with patch("subprocess.run") as mock_run, patch("nova.display._cprint"):
        dispatch_command("copy", agent, "")
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args
    assert b"something interesting" in call_kwargs[1]["input"]


def test_cmd_copy_no_assistant_message(agent):
    agent.messages = [{"role": "user", "content": "hello"}]
    printed = []
    with patch("subprocess.run") as mock_run, \
         patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("copy", agent, "")
    mock_run.assert_not_called()
    assert any("No response" in s for s in printed)


def test_cmd_copy_skips_empty_assistant_content(agent):
    agent.messages = [
        {"role": "assistant", "content": None},
        {"role": "assistant", "content": "real content"},
    ]
    with patch("subprocess.run") as mock_run, patch("nova.display._cprint"):
        dispatch_command("copy", agent, "")
    mock_run.assert_called_once()
    assert b"real content" in mock_run.call_args[1]["input"]


# ─── cmd_memory ──────────────────────────────────────────────────────────────


def test_cmd_memory_disabled(agent):
    agent.memory = None
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("memory", agent, "")
    assert any("disabled" in s for s in printed)


def test_cmd_memory_list_empty(agent, mock_memory_store):
    agent.memory = mock_memory_store
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("memory", agent, "list")
    assert any("No memories" in s for s in printed)


def test_cmd_memory_list_shows_entries(agent, mock_memory_store):
    mock_memory_store.add("User prefers dark mode")
    agent.memory = mock_memory_store
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("memory", agent, "list")
    assert any("dark mode" in s for s in printed)


def test_cmd_memory_clear(agent, mock_memory_store):
    mock_memory_store.add("something to forget")
    agent.memory = mock_memory_store
    with patch("nova.display._cprint"):
        dispatch_command("memory", agent, "clear")
    assert mock_memory_store.get_all() == []


def test_cmd_memory_search(agent, mock_memory_store):
    mock_memory_store.add("User likes Python")
    mock_memory_store.add("User dislikes Java")
    agent.memory = mock_memory_store
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("memory", agent, "search Python")
    assert any("Python" in s for s in printed)


def test_cmd_memory_default_lists_without_subcommand(agent, mock_memory_store):
    mock_memory_store.add("some fact")
    agent.memory = mock_memory_store
    printed = []
    with patch("nova.display._cprint", side_effect=lambda s: printed.append(s)):
        dispatch_command("memory", agent, "")
    assert any("some fact" in s for s in printed)
