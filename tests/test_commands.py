"""Tests for slash command registry and completion."""

import pytest

from nova.commands import (
    COMMAND_REGISTRY,
    CommandDef,
    SlashCompleter,
    get_commands_by_category,
    resolve_command,
)


def test_resolve_command_by_name():
    cmd = resolve_command("status")
    assert cmd is not None
    assert cmd.name == "status"


def test_resolve_command_by_alias():
    cmd = resolve_command("reset")
    assert cmd is not None
    assert cmd.name == "new"
    assert "reset" in cmd.aliases


def test_resolve_command_with_slash_prefix():
    cmd = resolve_command("/status")
    assert cmd is not None
    assert cmd.name == "status"


def test_resolve_command_case_insensitive():
    cmd1 = resolve_command("STATUS")
    cmd2 = resolve_command("Status")
    assert cmd1 is not None
    assert cmd2 is not None
    assert cmd1.name == cmd2.name


def test_resolve_command_not_found():
    cmd = resolve_command("nonexistent_xyz")
    assert cmd is None


def test_resolve_command_slash_and_alias():
    cmd = resolve_command("/reset")  # alias for "new"
    assert cmd is not None
    assert cmd.name == "new"


def test_get_commands_by_category():
    cats = get_commands_by_category()
    assert isinstance(cats, dict)
    assert len(cats) > 0
    assert "Session" in cats
    assert "Configuration" in cats


def test_get_commands_by_category_session_commands():
    cats = get_commands_by_category()
    session_cmds = cats.get("Session", [])
    assert len(session_cmds) > 0
    names = [cmd.name for cmd in session_cmds]
    assert "status" in names
    assert "history" in names


def test_get_commands_by_category_no_aliases_duplication():
    cats = get_commands_by_category()
    all_commands = []
    for cmd_list in cats.values():
        all_commands.extend([cmd.name for cmd in cmd_list])
    # Ensure no duplicates (aliases shouldn't appear separately)
    assert len(all_commands) == len(set(all_commands))


def test_command_registry_structure():
    assert len(COMMAND_REGISTRY) > 0
    for cmd in COMMAND_REGISTRY:
        assert isinstance(cmd, CommandDef)
        assert cmd.name, "Command must have a name"
        assert cmd.description, "Command must have a description"
        assert cmd.category, "Command must have a category"


def test_slash_completer_command_completion_prefix():
    completer = SlashCompleter()

    # Create a mock document and complete_event
    class MockDocument:
        def __init__(self, text):
            self.text_before_cursor = text

    completions = list(completer.get_completions(MockDocument("/sk"), None))
    assert len(completions) > 0
    # Should complete /sk to /skills
    completion_texts = [c.text for c in completions]
    assert any("ills" in text for text in completion_texts)


def test_slash_completer_command_completion_multiple():
    completer = SlashCompleter()

    class MockDocument:
        def __init__(self, text):
            self.text_before_cursor = text

    # /s should match "sessions", "skills" and others starting with s
    completions = list(completer.get_completions(MockDocument("/s"), None))
    assert len(completions) >= 2


def test_slash_completer_no_completion_without_slash():
    completer = SlashCompleter()

    class MockDocument:
        def __init__(self, text):
            self.text_before_cursor = text

    completions = list(completer.get_completions(MockDocument("status"), None))
    assert len(completions) == 0


def test_slash_completer_subcommand_completion():
    completer = SlashCompleter()

    class MockDocument:
        def __init__(self, text):
            self.text_before_cursor = text

    # /memory search should offer search, clear, list
    completions = list(completer.get_completions(MockDocument("/memory s"), None))
    completion_texts = [c.text for c in completions]
    assert len(completions) > 0
    assert any("earch" in text for text in completion_texts)


def test_slash_completer_subcommand_clear_and_list():
    completer = SlashCompleter()

    class MockDocument:
        def __init__(self, text):
            self.text_before_cursor = text

    # /memory should offer all subcommands
    completions = list(completer.get_completions(MockDocument("/memory "), None))
    completion_texts = [c.text for c in completions]
    assert len(completions) >= 2  # at least 2 subcommands


def test_slash_completer_no_subcommand_for_command_without_subcommands():
    completer = SlashCompleter()

    class MockDocument:
        def __init__(self, text):
            self.text_before_cursor = text

    # /status has no subcommands
    completions = list(completer.get_completions(MockDocument("/status a"), None))
    assert len(completions) == 0


def test_slash_completer_completion_display():
    completer = SlashCompleter()

    class MockDocument:
        def __init__(self, text):
            self.text_before_cursor = text

    completions = list(completer.get_completions(MockDocument("/sk"), None))
    assert len(completions) > 0

    # Check that display includes the full command name
    displays = [str(c.display) for c in completions]
    assert any("skills" in display for display in displays)

    # Display should include description as meta
    metas = [c.display_meta for c in completions]
    assert any(meta is not None for meta in metas)


def test_slash_completer_completion_with_args_hint():
    completer = SlashCompleter()

    class MockDocument:
        def __init__(self, text):
            self.text_before_cursor = text

    completions = list(completer.get_completions(MockDocument("/mod"), None))
    # /model has args_hint="[model]"
    displays = [str(c.display) for c in completions]
    assert any("[model]" in display for display in displays)
