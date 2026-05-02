"""Tests for the main agent loop.

Uses dependency injection to mock HTTP client, session store, and memory store.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import httpx

from nova.agent import NovaAgent
from nova.memory import MemoryStore
from nova.session import SessionStore
from nova.tools.registry import discover_builtin_tools


def _minimal_config() -> dict:
    """Return a minimal config for testing."""
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


def _mock_session_store():
    """Create a real SessionStore backed by a temp file."""
    tmpdir = tempfile.mkdtemp()
    return SessionStore(Path(tmpdir) / "test.db")


def _mock_response(status_code: int, json_data: dict) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = json.dumps(json_data)
    return resp


def test_agent_creation_with_injected_deps():
    """Test that agent accepts injected dependencies."""
    config = _minimal_config()
    session_store = _mock_session_store()
    mock_client = MagicMock(spec=httpx.Client)

    agent = NovaAgent(
        config=config,
        http_client=mock_client,
        session_store=session_store,
    )

    assert agent.session_store is session_store
    assert agent.client is mock_client
    assert agent.memory is None  # memory disabled in config
    assert agent.session_id is not None


def test_agent_creates_session_on_init():
    """Test that a new session is created when no session_id is provided."""
    config = _minimal_config()
    session_store = _mock_session_store()
    mock_client = MagicMock(spec=httpx.Client)

    agent = NovaAgent(
        config=config,
        http_client=mock_client,
        session_store=session_store,
    )

    assert agent.session_id is not None
    assert agent._system_prompt is not None
    assert "test agent" in agent._system_prompt


def test_agent_loads_existing_session():
    """Test that an existing session is loaded correctly."""
    config = _minimal_config()
    session_store = _mock_session_store()
    mock_client = MagicMock(spec=httpx.Client)

    # Create a session first
    agent1 = NovaAgent(
        config=config,
        http_client=mock_client,
        session_store=session_store,
    )
    session_id = agent1.session_id

    # Add a message
    session_store.add_message(session_id, "user", "hello")

    # Load the same session
    agent2 = NovaAgent(
        config=config,
        session_id=session_id,
        http_client=mock_client,
        session_store=session_store,
    )

    assert agent2.session_id == session_id
    messages = session_store.get_messages(session_id)
    assert len(messages) >= 1


def test_agent_run_no_tool_calls():
    """Test a simple run with no tool calls from the model."""
    config = _minimal_config()
    session_store = _mock_session_store()
    mock_client = MagicMock(spec=httpx.Client)

    llm_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "The answer is 42.",
            }
        }]
    }
    mock_client.post.return_value = _mock_response(200, llm_response)

    agent = NovaAgent(
        config=config,
        http_client=mock_client,
        session_store=session_store,
    )

    result = agent.run("What is the meaning of life?", stream=False)

    assert result == "The answer is 42."
    mock_client.post.assert_called_once()
    # Verify the payload includes the user message
    call_args = mock_client.post.call_args
    payload = call_args[1]["json"]
    assert any("meaning of life" in str(m.get("content", "")) for m in payload["messages"])


def test_agent_run_with_tool_call():
    """Test a run where the model calls a tool."""
    config = _minimal_config()
    session_store = _mock_session_store()
    mock_client = MagicMock(spec=httpx.Client)
    discover_builtin_tools()

    # First response: tool call, second response: final answer
    tool_call_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "terminal",
                        "arguments": json.dumps({"command": "echo hello"}),
                    },
                }],
            }
        }]
    }
    final_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "The command output was: hello",
            }
        }]
    }
    mock_client.post.side_effect = [
        _mock_response(200, tool_call_response),
        _mock_response(200, final_response),
    ]

    agent = NovaAgent(
        config=config,
        http_client=mock_client,
        session_store=session_store,
    )

    result = agent.run("Run echo hello", stream=False)

    assert result == "The command output was: hello"
    assert mock_client.post.call_count == 2


def test_agent_history_truncation():
    """Test that conversation history is trimmed when it exceeds the turn limit."""
    config = _minimal_config()
    config["budgets"]["conversation_turn_limit"] = 2  # Very small limit for testing
    session_store = _mock_session_store()
    mock_client = MagicMock(spec=httpx.Client)

    llm_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "OK",
            }
        }]
    }
    mock_client.post.return_value = _mock_response(200, llm_response)

    agent = NovaAgent(
        config=config,
        http_client=mock_client,
        session_store=session_store,
    )

    # Fill up history beyond the limit (turn_limit=2 means max 8 messages)
    for i in range(10):
        agent.messages.append({"role": "user", "content": f"msg {i}"})
        agent.messages.append({"role": "assistant", "content": f"reply {i}"})

    assert len(agent.messages) == 20

    # Run a turn — should trigger truncation
    agent.run("latest message", stream=False)

    # After truncation, should have at most 8 messages + the new ones
    assert len(agent.messages) <= 12  # 8 (trimmed) + 2 (new user+assistant)


def test_agent_execute_tool_call_invalid_json():
    """Test that invalid JSON in tool call arguments is handled gracefully."""
    config = _minimal_config()
    session_store = _mock_session_store()
    mock_client = MagicMock(spec=httpx.Client)

    agent = NovaAgent(
        config=config,
        http_client=mock_client,
        session_store=session_store,
    )

    tool_call = {
        "id": "call_bad",
        "function": {
            "name": "terminal",
            "arguments": "{not valid json",
        },
    }

    result = agent._execute_tool_call(tool_call)
    assert "Error" in result
    assert "Invalid JSON" in result


def test_agent_execute_tool_call_unknown_tool():
    """Test that unknown tool names return an error."""
    config = _minimal_config()
    session_store = _mock_session_store()
    mock_client = MagicMock(spec=httpx.Client)

    agent = NovaAgent(
        config=config,
        http_client=mock_client,
        session_store=session_store,
    )

    tool_call = {
        "id": "call_unknown",
        "function": {
            "name": "nonexistent_tool_xyz",
            "arguments": "{}",
        },
    }

    result = agent._execute_tool_call(tool_call)
    assert "Error" in result


def test_agent_build_system_prompt_with_memory():
    """Test that system prompt includes memory content when memory is enabled."""
    config = _minimal_config()
    config["memory"]["enabled"] = True
    session_store = _mock_session_store()
    mock_client = MagicMock(spec=httpx.Client)

    # Create a real memory store in a temp dir
    tmpdir = tempfile.mkdtemp()
    memory = MemoryStore(Path(tmpdir) / "memory.json", max_entries=10)
    memory.add("User prefers dark mode")

    agent = NovaAgent(
        config=config,
        http_client=mock_client,
        session_store=session_store,
        memory_store=memory,
    )

    assert agent.memory is not None
    assert agent._system_prompt is not None
    assert "dark mode" in agent._system_prompt


def test_agent_refresh_system_prompt():
    """Test that _refresh_system_prompt updates the prompt and session."""
    config = _minimal_config()
    config["memory"]["enabled"] = True
    session_store = _mock_session_store()
    mock_client = MagicMock(spec=httpx.Client)

    tmpdir = tempfile.mkdtemp()
    memory = MemoryStore(Path(tmpdir) / "memory.json", max_entries=10)

    agent = NovaAgent(
        config=config,
        http_client=mock_client,
        session_store=session_store,
        memory_store=memory,
    )

    initial_prompt = agent._system_prompt

    # Add a memory and refresh
    memory.add("New fact: user lives in NYC")
    agent._refresh_system_prompt()

    assert agent._system_prompt != initial_prompt or "NYC" in agent._system_prompt
    # Verify session was updated
    info = session_store.get_session_info(agent.session_id)
    assert "NYC" in info.get("system_prompt", "")


def test_agent_max_iterations_limit():
    """Test that the agent stops after max_iterations."""
    config = _minimal_config()
    config["agent"]["max_iterations"] = 2
    session_store = _mock_session_store()
    mock_client = MagicMock(spec=httpx.Client)
    discover_builtin_tools()

    # Always return a tool call — should stop after 2 iterations
    tool_call_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_loop",
                    "type": "function",
                    "function": {
                        "name": "terminal",
                        "arguments": json.dumps({"command": "echo test"}),
                    },
                }],
            }
        }]
    }
    mock_client.post.return_value = _mock_response(200, tool_call_response)

    agent = NovaAgent(
        config=config,
        http_client=mock_client,
        session_store=session_store,
    )

    agent.run("test", stream=False)

    # Should have called the API exactly max_iterations times
    assert mock_client.post.call_count == 2
