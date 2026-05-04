"""Tests for the search_sessions tool."""

import tempfile
from pathlib import Path

import pytest

from nova.session import SessionStore
from nova.tools.search_sessions_tool import _search_sessions_tool


@pytest.fixture
def temp_session_store() -> SessionStore:
    """Create a temporary session store with sample sessions."""
    tmpdir = tempfile.mkdtemp()
    store = SessionStore(Path(tmpdir) / "sessions.db")

    # Create some test sessions with different content
    session1 = store.create_session(title="Python Tips")
    store.add_message(session1, "user", "How do I use list comprehensions?")
    store.add_message(session1, "assistant", "List comprehensions are a concise way to create lists in Python.")
    store.add_message(session1, "user", "Can you show me an example?")
    store.add_message(session1, "assistant", "[x*2 for x in range(10)] creates a list of doubled numbers.")

    session2 = store.create_session(title="Docker Setup")
    store.add_message(session2, "user", "How do I containerize my application?")
    store.add_message(session2, "assistant", "You'll need a Dockerfile and docker-compose.yml")
    store.add_message(session2, "user", "What's the difference between images and containers?")
    store.add_message(session2, "assistant", "Images are templates, containers are running instances.")

    session3 = store.create_session(title="Database Design")
    store.add_message(session3, "user", "How do I normalize a database schema?")
    store.add_message(session3, "assistant", "Normalization reduces redundancy and improves data integrity.")

    return store


def test_search_sessions_found(temp_session_store):
    """Test searching for sessions with matching content."""
    result = _search_sessions_tool(
        {"query": "Python"},
        session_store=temp_session_store,
    )
    assert "Found" in result
    assert "Python Tips" in result
    # Verify session information is included
    assert "Updated:" in result


def test_search_sessions_multiple_matches(temp_session_store):
    """Test search that matches multiple sessions."""
    result = _search_sessions_tool(
        {"query": "How do I"},
        session_store=temp_session_store,
    )
    assert "Found" in result
    # Should match multiple sessions since all have this pattern
    assert result.count("[") >= 2


def test_search_sessions_not_found(temp_session_store):
    """Test searching for non-existent content."""
    result = _search_sessions_tool(
        {"query": "nonexistent_keyword_xyz"},
        session_store=temp_session_store,
    )
    assert "No sessions found" in result


def test_search_sessions_empty_query(temp_session_store):
    """Test searching with empty query."""
    result = _search_sessions_tool(
        {"query": ""},
        session_store=temp_session_store,
    )
    assert "Error" in result
    assert "required" in result


def test_search_sessions_with_limit(temp_session_store):
    """Test search with limit parameter."""
    result = _search_sessions_tool(
        {"query": "How", "limit": 1},
        session_store=temp_session_store,
    )
    assert "Found" in result
    # Should limit results
    assert result.count("\n1.") == 1


def test_search_sessions_limit_clamping(temp_session_store):
    """Test that limit is clamped to valid range."""
    # Test too high limit
    result_high = _search_sessions_tool(
        {"query": "How", "limit": 1000},
        session_store=temp_session_store,
    )
    assert "Found" in result_high

    # Test negative limit
    result_negative = _search_sessions_tool(
        {"query": "How", "limit": -5},
        session_store=temp_session_store,
    )
    assert "Found" in result_negative


def test_search_sessions_invalid_limit(temp_session_store):
    """Test that invalid limit defaults to 10."""
    result = _search_sessions_tool(
        {"query": "How", "limit": "not_a_number"},
        session_store=temp_session_store,
    )
    assert "Found" in result


def test_search_sessions_no_store():
    """Test error when session store is not available."""
    result = _search_sessions_tool(
        {"query": "test"},
        session_store=None,
    )
    assert "Error" in result
    assert "not available" in result


def test_search_sessions_case_insensitive(temp_session_store):
    """Test that search is case-insensitive."""
    result_lower = _search_sessions_tool(
        {"query": "python"},
        session_store=temp_session_store,
    )
    result_upper = _search_sessions_tool(
        {"query": "PYTHON"},
        session_store=temp_session_store,
    )
    # Both should find the same session
    assert "Python Tips" in result_lower
    assert "Python Tips" in result_upper


def test_search_sessions_format(temp_session_store):
    """Test that results are properly formatted."""
    result = _search_sessions_tool(
        {"query": "Docker"},
        session_store=temp_session_store,
    )
    # Check formatting includes expected fields
    assert "Found" in result
    assert "Docker Setup" in result
    assert "Updated:" in result
    assert "Messages:" in result
    assert "[" in result  # Session ID in brackets


def test_search_sessions_title_search(temp_session_store):
    """Test that search works on session titles."""
    result = _search_sessions_tool(
        {"query": "Database"},
        session_store=temp_session_store,
    )
    assert "Found" in result
    assert "Database Design" in result


def test_search_sessions_message_content_search(temp_session_store):
    """Test that search works on message content."""
    result = _search_sessions_tool(
        {"query": "containers"},
        session_store=temp_session_store,
    )
    assert "Found" in result
    assert "Docker Setup" in result
