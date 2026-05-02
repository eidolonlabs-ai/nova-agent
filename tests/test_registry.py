"""Tests for the tool registry."""

from nova.tools.registry import discover_builtin_tools, registry


def test_discover_builtin_tools():
    discover_builtin_tools()
    assert "terminal" in registry.all_tool_names
    assert "read_file" in registry.all_tool_names
    assert "write_file" in registry.all_tool_names


def test_get_definitions():
    discover_builtin_tools()
    tools = registry.get_definitions()
    assert len(tools) > 0
    for tool in tools:
        assert "type" in tool
        assert tool["type"] == "function"
        assert "function" in tool
        assert "name" in tool["function"]
        assert "parameters" in tool["function"]


def test_get_tool_summary_list():
    discover_builtin_tools()
    summary = registry.get_tool_summary_list()
    assert "terminal" in summary
    assert "read_file" in summary


def test_dispatch_unknown_tool():
    result = registry.dispatch("nonexistent_tool", {})
    assert "Error" in result
    assert "nonexistent_tool" in result
