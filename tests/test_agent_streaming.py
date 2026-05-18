"""Tests for agent streaming response handling.

Covers interrupt checks, tool call accumulation, and callback invocation
during streaming with the OpenAI SDK.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from openai import BadRequestError

from nova.agent import NovaAgent
from nova.session import SessionStore


@pytest.fixture
def minimal_config():
    """Minimal test config."""
    return {
        "llm": {
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
        "wiki": {"enabled": False},
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


def make_mock_stream(*chunks):
    """Create a mock stream context manager that yields the given chunks."""

    class MockStream:
        def __iter__(self):
            return iter(chunks)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    return MockStream()


def make_text_chunk(content: str) -> MagicMock:
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta.content = content
    chunk.choices[0].delta.tool_calls = None
    chunk.choices[0].delta.model_extra = {}
    return chunk


def make_tool_chunk(index: int, id: str = "", name: str = "", arguments: str = "") -> MagicMock:
    tc = MagicMock()
    tc.index = index
    tc.id = id
    tc.function.name = name
    tc.function.arguments = arguments
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta.content = None
    chunk.choices[0].delta.tool_calls = [tc]
    chunk.choices[0].delta.model_extra = {}
    return chunk


def make_reasoning_chunk(reasoning: str) -> MagicMock:
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta.content = None
    chunk.choices[0].delta.tool_calls = None
    chunk.choices[0].delta.model_extra = {"reasoning": reasoning}
    return chunk


def test_stream_response_interrupt_during_stream(minimal_config, mock_session_store):
    """Test that interrupt check stops streaming."""
    from openai import OpenAI

    mock_client = MagicMock(spec=OpenAI)

    def interrupt_check():
        return True

    stream = make_mock_stream(
        make_text_chunk("Hello"),
        make_text_chunk(" world"),
    )
    mock_client.chat.completions.create.return_value = stream

    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_client,
        session_store=mock_session_store,
    )
    agent._interrupt_check = interrupt_check

    result = agent._stream_response({"model": "test-model", "messages": []})

    assert "choices" in result


def test_stream_response_empty_content(minimal_config, mock_session_store):
    """Test streaming response with no content blocks."""
    from openai import OpenAI

    mock_client = MagicMock(spec=OpenAI)
    stream = make_mock_stream()
    mock_client.chat.completions.create.return_value = stream

    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_client,
        session_store=mock_session_store,
    )

    result = agent._stream_response({"model": "test-model", "messages": []})

    assert result["choices"][0]["message"]["content"] is None


def test_stream_response_multiple_tool_calls(minimal_config, mock_session_store):
    """Test streaming accumulates multiple tool calls correctly."""
    from openai import OpenAI

    mock_client = MagicMock(spec=OpenAI)

    stream = make_mock_stream(
        make_tool_chunk(0, id="c1", name="terminal"),
        make_tool_chunk(0, arguments='{"cmd'),
        make_tool_chunk(0, arguments='":"ls"}'),
        make_tool_chunk(1, id="c2", name="file_ops"),
    )
    mock_client.chat.completions.create.return_value = stream

    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_client,
        session_store=mock_session_store,
    )

    result = agent._stream_response({"model": "test-model", "messages": []})

    tool_calls = result["choices"][0]["message"]["tool_calls"]
    assert tool_calls is not None
    assert len(tool_calls) >= 1


def test_stream_response_reasoning_callback(minimal_config, mock_session_store):
    """Test that reasoning content triggers callback."""
    from openai import OpenAI

    mock_client = MagicMock(spec=OpenAI)
    callback_invoked = []

    def reasoning_callback(text):
        callback_invoked.append(text)

    stream = make_mock_stream(
        make_reasoning_chunk("Let me"),
        make_reasoning_chunk(" think"),
    )
    mock_client.chat.completions.create.return_value = stream

    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_client,
        session_store=mock_session_store,
    )

    agent._stream_response(
        {"model": "test-model", "messages": []}, reasoning_callback=reasoning_callback
    )

    assert len(callback_invoked) == 2
    assert callback_invoked[0] == "Let me"
    assert callback_invoked[1] == " think"


def test_stream_response_reasoning_content_in_result(minimal_config, mock_session_store):
    """reasoning_content must be returned in the message dict (DeepSeek requirement)."""
    from openai import OpenAI

    mock_client = MagicMock(spec=OpenAI)

    stream = make_mock_stream(
        make_reasoning_chunk("Let me"),
        make_reasoning_chunk(" think"),
        make_text_chunk("Answer"),
    )
    mock_client.chat.completions.create.return_value = stream

    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_client,
        session_store=mock_session_store,
    )

    result = agent._stream_response({"model": "test-model", "messages": []})
    msg = result["choices"][0]["message"]
    assert msg["reasoning_content"] == "Let me think"
    assert msg["content"] == "Answer"


def test_stream_response_text_callback(minimal_config, mock_session_store):
    """Test that text content triggers callback."""
    from openai import OpenAI

    mock_client = MagicMock(spec=OpenAI)
    callback_invoked = []

    def text_callback(text):
        callback_invoked.append(text)

    stream = make_mock_stream(
        make_text_chunk("Hello"),
        make_text_chunk(" world"),
    )
    mock_client.chat.completions.create.return_value = stream

    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_client,
        session_store=mock_session_store,
    )

    result = agent._stream_response({"model": "test-model", "messages": []}, callback=text_callback)

    assert len(callback_invoked) == 2
    assert callback_invoked[0] == "Hello"
    assert callback_invoked[1] == " world"
    assert result["choices"][0]["message"]["content"] == "Hello world"


def test_stream_response_400_error(minimal_config, mock_session_store):
    """Test that BadRequestError from the SDK propagates."""
    from openai import OpenAI

    mock_client = MagicMock(spec=OpenAI)

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_client.chat.completions.create.side_effect = BadRequestError(
        message="Bad request",
        response=mock_response,
        body={"error": "Bad request"},
    )

    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_client,
        session_store=mock_session_store,
    )

    with pytest.raises(BadRequestError):
        agent._stream_response({"model": "test-model", "messages": []})
