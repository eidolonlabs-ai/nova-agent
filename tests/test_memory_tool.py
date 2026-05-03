"""Tests for the memory tool."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nova.memory import MemoryStore
from nova.tools.memory_tool import _memory_tool


@pytest.fixture
def temp_memory() -> MemoryStore:
    tmpdir = tempfile.mkdtemp()
    return MemoryStore(Path(tmpdir) / "memory.json", max_entries=10)


def test_memory_tool_add_success(temp_memory):
    result = _memory_tool(
        {"action": "add", "content": "User likes Python"},
        memory=temp_memory,
    )
    data = json.loads(result)
    assert data["status"] == "saved"
    assert "id" in data


def test_memory_tool_add_with_category(temp_memory):
    result = _memory_tool(
        {"action": "add", "content": "Some fact", "category": "preferences"},
        memory=temp_memory,
    )
    data = json.loads(result)
    assert data["status"] == "saved"
    entries = temp_memory.get_all()
    assert entries[0]["category"] == "preferences"


def test_memory_tool_add_missing_content(temp_memory):
    result = _memory_tool(
        {"action": "add", "content": ""},
        memory=temp_memory,
    )
    assert "Error" in result


def test_memory_tool_search_found(temp_memory):
    temp_memory.add("User prefers dark mode")
    result = _memory_tool(
        {"action": "search", "query": "dark"},
        memory=temp_memory,
    )
    data = json.loads(result)
    assert len(data) > 0
    assert "dark" in data[0]["content"]


def test_memory_tool_search_not_found(temp_memory):
    temp_memory.add("something unrelated")
    result = _memory_tool(
        {"action": "search", "query": "xyz123"},
        memory=temp_memory,
    )
    assert "No memories found" in result


def test_memory_tool_search_missing_query(temp_memory):
    result = _memory_tool(
        {"action": "search", "query": ""},
        memory=temp_memory,
    )
    assert "Error" in result


def test_memory_tool_delete_success(temp_memory):
    entry = temp_memory.add("something to delete")
    result = _memory_tool(
        {"action": "delete", "id": entry["id"]},
        memory=temp_memory,
    )
    data = json.loads(result)
    assert data["status"] == "deleted"


def test_memory_tool_delete_not_found(temp_memory):
    result = _memory_tool(
        {"action": "delete", "id": "nonexistent"},
        memory=temp_memory,
    )
    data = json.loads(result)
    assert data["status"] == "not_found"


def test_memory_tool_delete_missing_id(temp_memory):
    result = _memory_tool(
        {"action": "delete", "id": ""},
        memory=temp_memory,
    )
    assert "Error" in result


def test_memory_tool_clear_success(temp_memory):
    temp_memory.add("entry 1")
    temp_memory.add("entry 2")
    result = _memory_tool(
        {"action": "clear"},
        memory=temp_memory,
    )
    data = json.loads(result)
    assert data["status"] == "cleared"
    assert len(temp_memory.get_all()) == 0


def test_memory_tool_unknown_action(temp_memory):
    result = _memory_tool(
        {"action": "invalid_action"},
        memory=temp_memory,
    )
    assert "Error" in result
    assert "Unknown action" in result


def test_memory_tool_no_memory_store():
    result = _memory_tool(
        {"action": "add", "content": "test"},
        memory=None,
    )
    assert "Error" in result
    assert "not enabled" in result


def test_memory_tool_refresh_on_add(temp_memory):
    mock_agent = MagicMock()
    mock_agent._refresh_system_prompt = MagicMock()
    result = _memory_tool(
        {"action": "add", "content": "test fact"},
        memory=temp_memory,
        agent=mock_agent,
    )
    assert json.loads(result)["status"] == "saved"
    mock_agent._refresh_system_prompt.assert_called_once()


def test_memory_tool_refresh_on_delete(temp_memory):
    entry = temp_memory.add("fact to remove")
    mock_agent = MagicMock()
    mock_agent._refresh_system_prompt = MagicMock()
    _memory_tool(
        {"action": "delete", "id": entry["id"]},
        memory=temp_memory,
        agent=mock_agent,
    )
    mock_agent._refresh_system_prompt.assert_called_once()


def test_memory_tool_refresh_on_clear(temp_memory):
    temp_memory.add("entry 1")
    mock_agent = MagicMock()
    mock_agent._refresh_system_prompt = MagicMock()
    _memory_tool(
        {"action": "clear"},
        memory=temp_memory,
        agent=mock_agent,
    )
    mock_agent._refresh_system_prompt.assert_called_once()


def test_memory_tool_no_refresh_on_search(temp_memory):
    temp_memory.add("test")
    mock_agent = MagicMock()
    _memory_tool(
        {"action": "search", "query": "test"},
        memory=temp_memory,
        agent=mock_agent,
    )
    mock_agent._refresh_system_prompt.assert_not_called()


def test_memory_tool_agent_without_refresh_method(temp_memory):
    mock_agent = MagicMock(spec=[])  # No _refresh_system_prompt
    result = _memory_tool(
        {"action": "add", "content": "test"},
        memory=temp_memory,
        agent=mock_agent,
    )
    assert json.loads(result)["status"] == "saved"  # Should still work
