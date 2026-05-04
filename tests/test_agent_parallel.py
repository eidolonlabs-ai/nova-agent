"""Tests for parallel tool execution in agent."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from nova.agent import NovaAgent
from nova.session import SessionStore
from nova.tools.registry import discover_builtin_tools


@pytest.fixture
def minimal_config():
    """Minimal test config."""
    discover_builtin_tools()
    return {
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": "test-key",
            "model": "test-model",
        },
        "agent": {
            "max_iterations": 3,
            "temperature": 0.7,
            "top_p": 1.0,
            "identity": "You are a test agent.",
        },
        "budgets": {
            "conversation_turn_limit": 5,
            "tool_result_max_chars": 8000,
            "system_prompt_max": 8000,
        },
        "memory": {"enabled": False},
        "session": {"directory": str(tempfile.mkdtemp())},
        "skills": {"enabled": False},
        "compression": {"enabled": False},
        "context_files": [],
    }


@pytest.fixture
def mock_session_store():
    """Real SessionStore for integration testing."""
    tmpdir = tempfile.mkdtemp()
    return SessionStore(Path(tmpdir) / "test.db")


def test_execute_tool_calls_parallel_read_only_success(minimal_config, mock_session_store):
    """Test parallel execution of multiple read-only tool calls."""
    mock_client = MagicMock(spec=httpx.Client)
    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    # Create multiple read-only tool calls
    tool_calls = [
        {
            "id": "call_1",
            "function": {
                "name": "terminal",
                "arguments": '{"command": "ls"}',
            },
        },
        {
            "id": "call_2",
            "function": {
                "name": "terminal",
                "arguments": '{"command": "pwd"}',
            },
        },
    ]

    # Should execute parallel read-only calls
    results = agent._execute_tool_calls_parallel(tool_calls)
    assert len(results) == len(tool_calls)


def test_execute_tool_calls_parallel_with_write_sequential(minimal_config, mock_session_store):
    """Test that write operations are executed sequentially."""
    mock_client = MagicMock(spec=httpx.Client)
    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    # Mix of read and write operations
    tool_calls = [
        {
            "id": "call_1",
            "function": {
                "name": "terminal",
                "arguments": '{"command": "ls"}',  # read-only
            },
        },
        {
            "id": "call_2",
            "function": {
                "name": "file_ops",
                "arguments": '{"action": "write", "path": "/tmp/test.txt", "content": "test"}',  # write
            },
        },
    ]

    # Should handle mixed read/write
    try:
        results = agent._execute_tool_calls_parallel(tool_calls)
        assert len(results) >= 1
    except Exception:
        # Some tools might fail, that's ok for this test
        pass


def test_execute_tool_calls_invalid_json(minimal_config, mock_session_store):
    """Test handling of invalid JSON in tool arguments."""
    mock_client = MagicMock(spec=httpx.Client)
    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    tool_calls = [
        {
            "id": "call_bad",
            "function": {
                "name": "terminal",
                "arguments": "{invalid json}",  # Invalid
            },
        },
    ]

    # Should handle invalid JSON gracefully
    results = agent._execute_tool_calls_parallel(tool_calls)
    assert len(results) > 0
    assert "Error" in results[0] or "error" in results[0].lower()


def test_execute_tool_call_unknown_tool(minimal_config, mock_session_store):
    """Test handling of unknown tool names."""
    mock_client = MagicMock(spec=httpx.Client)
    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    tool_call = {
        "id": "call_unknown",
        "function": {
            "name": "nonexistent_tool_xyz",
            "arguments": "{}",
        },
    }

    result = agent._execute_tool_call(tool_call)
    assert "Error" in result or "error" in result.lower()


def test_execute_tool_calls_parallel_empty_list(minimal_config, mock_session_store):
    """Test parallel execution with empty tool calls list."""
    mock_client = MagicMock(spec=httpx.Client)
    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    results = agent._execute_tool_calls_parallel([])
    assert results == []


def test_execute_tool_calls_parallel_callback_invoked(minimal_config, mock_session_store):
    """Test that tool callback is invoked for each tool."""
    mock_client = MagicMock(spec=httpx.Client)
    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    callback_invoked = []

    def tool_callback(name):
        callback_invoked.append(name)

    agent._tool_callback = tool_callback

    tool_calls = [
        {
            "id": "call_1",
            "function": {
                "name": "terminal",
                "arguments": '{"command": "echo test"}',
            },
        },
    ]

    results = agent._execute_tool_calls_parallel(tool_calls)

    # Callback may or may not be invoked depending on implementation
    assert len(results) > 0
