"""Tests for the wiki tool."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nova.tools.wiki_tool import _wiki_tool
from nova.wiki_memory import WikiMemory


@pytest.fixture
def wiki(tmp_path: Path) -> WikiMemory:
    return WikiMemory(tmp_path / "wiki")


def test_wiki_tool_no_wiki_store():
    result = _wiki_tool({"action": "write", "title": "x", "content": "y"})
    assert "Error" in result
    assert "not enabled" in result


def test_write_action(wiki: WikiMemory):
    result = _wiki_tool(
        {"action": "write", "title": "Test", "content": "Hello", "tags": ["demo"]},
        wiki=wiki,
    )
    data = json.loads(result)
    assert data["status"] == "written"


def test_write_missing_title(wiki: WikiMemory):
    result = _wiki_tool({"action": "write", "content": "x"}, wiki=wiki)
    assert "Error" in result


def test_write_missing_content(wiki: WikiMemory):
    result = _wiki_tool({"action": "write", "title": "T"}, wiki=wiki)
    assert "Error" in result


def test_append_action(wiki: WikiMemory):
    wiki.write("Note", "First")
    result = _wiki_tool(
        {"action": "append", "title": "Note", "content": "Second"},
        wiki=wiki,
    )
    data = json.loads(result)
    assert data["status"] == "appended"


def test_append_missing_title(wiki: WikiMemory):
    result = _wiki_tool({"action": "append", "content": "x"}, wiki=wiki)
    assert "Error" in result


def test_read_existing(wiki: WikiMemory):
    wiki.write("My Note", "Some content", tags=["tag1"])
    result = _wiki_tool({"action": "read", "title": "My Note"}, wiki=wiki)
    assert "My Note" in result
    assert "Some content" in result
    assert "#tag1" in result


def test_read_missing(wiki: WikiMemory):
    result = _wiki_tool({"action": "read", "title": "Ghost"}, wiki=wiki)
    assert "not found" in result.lower()


def test_read_missing_title_param(wiki: WikiMemory):
    result = _wiki_tool({"action": "read"}, wiki=wiki)
    assert "Error" in result


def test_search_found(wiki: WikiMemory):
    wiki.write("Alpha", "contains the keyword needle")
    result = _wiki_tool({"action": "search", "query": "needle"}, wiki=wiki)
    data = json.loads(result)
    assert len(data) == 1
    assert data[0]["title"] == "Alpha"


def test_search_not_found(wiki: WikiMemory):
    wiki.write("Note", "no match here")
    result = _wiki_tool({"action": "search", "query": "zzz_absent"}, wiki=wiki)
    assert "No notes found" in result


def test_search_missing_query(wiki: WikiMemory):
    result = _wiki_tool({"action": "search"}, wiki=wiki)
    assert "Error" in result


def test_list_action(wiki: WikiMemory):
    wiki.write("A", "content")
    wiki.write("B", "content")
    result = _wiki_tool({"action": "list"}, wiki=wiki)
    data = json.loads(result)
    titles = {n["title"] for n in data}
    assert "A" in titles
    assert "B" in titles


def test_list_empty(wiki: WikiMemory):
    result = _wiki_tool({"action": "list"}, wiki=wiki)
    assert "No notes found" in result


def test_list_filter_by_tag(wiki: WikiMemory):
    wiki.write("Tagged", "x", tags=["keep"])
    wiki.write("Other", "y", tags=["drop"])
    result = _wiki_tool({"action": "list", "tag": "keep"}, wiki=wiki)
    data = json.loads(result)
    assert len(data) == 1
    assert data[0]["title"] == "Tagged"


def test_delete_action(wiki: WikiMemory):
    wiki.write("Bye", "farewell")
    result = _wiki_tool({"action": "delete", "title": "Bye"}, wiki=wiki)
    data = json.loads(result)
    assert data["status"] == "deleted"
    assert wiki.read("Bye") is None


def test_delete_not_found(wiki: WikiMemory):
    result = _wiki_tool({"action": "delete", "title": "Ghost"}, wiki=wiki)
    data = json.loads(result)
    assert data["status"] == "not_found"


def test_delete_missing_title(wiki: WikiMemory):
    result = _wiki_tool({"action": "delete"}, wiki=wiki)
    assert "Error" in result


def test_unknown_action(wiki: WikiMemory):
    result = _wiki_tool({"action": "explode"}, wiki=wiki)
    assert "Unknown action" in result


def test_maintenance_action_returns_report(wiki: WikiMemory):
    wiki.write("A", "content")
    wiki.write("B", "linked to [[A]]")
    result = _wiki_tool({"action": "maintenance"}, wiki=wiki)
    report = json.loads(result)
    assert report["total_notes"] == 2
    assert "duplicate_candidates" in report
    assert "orphans" in report
    assert "stale" in report
    assert "tag_counts" in report


def test_maintenance_does_not_refresh_prompt(wiki: WikiMemory):
    """Maintenance is read-only — should not trigger system prompt rebuild."""
    from unittest.mock import MagicMock

    agent = MagicMock()
    _wiki_tool({"action": "maintenance"}, wiki=wiki, agent=agent)
    agent._refresh_system_prompt.assert_not_called()


def test_path_traversal_returns_error_not_raise(wiki: WikiMemory):
    result = _wiki_tool(
        {"action": "write", "title": "../../etc/passwd", "content": "evil"},
        wiki=wiki,
    )
    assert "Error" in result
    assert "path traversal" in result


def test_write_triggers_agent_refresh(wiki: WikiMemory):
    agent = MagicMock()
    _wiki_tool(
        {"action": "write", "title": "T", "content": "c"},
        wiki=wiki,
        agent=agent,
    )
    agent._refresh_system_prompt.assert_called_once()
