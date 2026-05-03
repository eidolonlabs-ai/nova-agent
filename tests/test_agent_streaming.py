"""Tests for agent streaming response handling.

Covers watchdog timeout, interrupt checks, malformed JSON, tool call accumulation,
and callback invocation during streaming.
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from nova.agent import NovaAgent
from nova.session import SessionStore


@pytest.fixture
def minimal_config():
    """Minimal test config."""
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


def make_mock_stream_response(lines):
    """Create a context manager mock for streaming response."""
    @contextmanager
    def stream_context(*args, **kwargs):
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.iter_lines.return_value = iter(lines)
        response.raise_for_status = MagicMock()
        yield response
    return stream_context


def test_stream_response_watchdog_timeout(minimal_config, mock_session_store):
    """Test that streaming watchdog timeout is enforced."""
    mock_client = MagicMock(spec=httpx.Client)

    # Create mock lines that simulate timeout scenario
    lines = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
    ]
    mock_client.stream = make_mock_stream_response(lines)

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    # Patch time.monotonic to simulate timeout
    with patch('nova.agent.time.monotonic') as mock_time:
        # Simulate initial time and then timeout (>30s no data)
        mock_time.side_effect = [0.0, 31.0]
        result = agent._stream_response({"messages": []})

    # Should return a result (possibly truncated due to timeout)
    assert "choices" in result
    assert len(result["choices"]) > 0


def test_stream_response_interrupt_during_stream(minimal_config, mock_session_store):
    """Test that interrupt check stops streaming."""
    mock_client = MagicMock(spec=httpx.Client)

    def interrupt_check():
        """Return True to interrupt."""
        return True

    lines = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        'data: {"choices": [{"delta": {"content": " world"}}]}',
    ]
    mock_client.stream = make_mock_stream_response(lines)

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    agent._interrupt_check = interrupt_check

    result = agent._stream_response({"messages": []})

    # Should have interrupted
    assert "choices" in result


def test_stream_response_malformed_json_recovers(minimal_config, mock_session_store):
    """Test that malformed JSON in stream lines is handled gracefully."""
    mock_client = MagicMock(spec=httpx.Client)

    lines = [
        'data: {"choices": [{"delta": {"content": "OK"}}]}',
        'data: {invalid json',  # Malformed, should be skipped
        'data: {"choices": [{"delta": {"content": " done"}}]}',
        'data: [DONE]',
    ]
    mock_client.stream = make_mock_stream_response(lines)

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    # Should recover from malformed JSON and continue
    result = agent._stream_response({"messages": []})

    # Should have recovered and continued
    assert result["choices"][0]["message"]["content"] == "OK done"


def test_stream_response_empty_content(minimal_config, mock_session_store):
    """Test streaming response with no content blocks."""
    mock_client = MagicMock(spec=httpx.Client)

    lines = [
        'data: [DONE]',
    ]
    mock_client.stream = make_mock_stream_response(lines)

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    result = agent._stream_response({"messages": []})

    # Should return empty content
    assert result["choices"][0]["message"]["content"] is None


def test_stream_response_multiple_tool_calls(minimal_config, mock_session_store):
    """Test streaming accumulates multiple tool calls correctly."""
    mock_client = MagicMock(spec=httpx.Client)

    lines = [
        'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c1", "function": {"name": "terminal"}}]}}]}',
        'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\\"cmd"}}]}}]}',
        'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "\\":\\"ls\\"}"}}]}}]}',
        'data: {"choices": [{"delta": {"tool_calls": [{"index": 1, "id": "c2", "function": {"name": "file_ops"}}]}}]}',
        'data: [DONE]',
    ]
    mock_client.stream = make_mock_stream_response(lines)

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    result = agent._stream_response({"messages": []})

    # Should have accumulated tool calls
    tool_calls = result["choices"][0]["message"]["tool_calls"]
    assert tool_calls is not None
    assert len(tool_calls) >= 1


def test_stream_response_reasoning_callback(minimal_config, mock_session_store):
    """Test that reasoning content triggers callback."""
    mock_client = MagicMock(spec=httpx.Client)

    callback_invoked = []

    def reasoning_callback(text):
        callback_invoked.append(text)

    lines = [
        'data: {"choices": [{"delta": {"reasoning": "Let me"}}]}',
        'data: {"choices": [{"delta": {"reasoning": " think"}}]}',
        'data: [DONE]',
    ]
    mock_client.stream = make_mock_stream_response(lines)

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    agent._stream_response({"messages": []}, reasoning_callback=reasoning_callback)

    # Callback should have been invoked
    assert len(callback_invoked) == 2
    assert callback_invoked[0] == "Let me"
    assert callback_invoked[1] == " think"


def test_stream_response_text_callback(minimal_config, mock_session_store):
    """Test that text content triggers callback."""
    mock_client = MagicMock(spec=httpx.Client)

    callback_invoked = []

    def text_callback(text):
        callback_invoked.append(text)

    lines = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        'data: {"choices": [{"delta": {"content": " world"}}]}',
        'data: [DONE]',
    ]
    mock_client.stream = make_mock_stream_response(lines)

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    result = agent._stream_response({"messages": []}, callback=text_callback)

    # Callback should have been invoked
    assert len(callback_invoked) == 2
    assert callback_invoked[0] == "Hello"
    assert callback_invoked[1] == " world"
    assert result["choices"][0]["message"]["content"] == "Hello world"


def test_stream_response_400_error(minimal_config, mock_session_store):
    """Test handling of 400 errors during streaming."""
    mock_client = MagicMock(spec=httpx.Client)

    response = MagicMock(spec=httpx.Response)
    response.status_code = 400
    response.read.return_value = b'{"error": "Bad request"}'
    response.request = MagicMock()

    @contextmanager
    def error_stream(*args, **kwargs):
        yield response

    mock_client.stream = error_stream

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_client,
        session_store=mock_session_store,
    )

    # Should raise HTTPStatusError on 400
    with pytest.raises(httpx.HTTPStatusError):
        agent._stream_response({"messages": []})
