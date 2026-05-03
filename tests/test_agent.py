"""Tests for the main agent loop.

Uses dependency injection to mock HTTP client, session store, and memory store.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import httpx

from nova.agent import NovaAgent
from nova.tools.registry import discover_builtin_tools


def make_mock_response(status_code: int = 200, json_data: dict | None = None, text: str | None = None) -> MagicMock:
    """Create a generic mock httpx.Response."""
    if json_data is None:
        json_data = {}
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = text or json.dumps(json_data)
    resp.headers = {}
    return resp



def test_agent_creation_with_injected_deps(minimal_config, mock_session_store, mock_http_client):
    """Test that agent accepts injected dependencies."""
    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    assert agent.session_store is mock_session_store
    assert agent.client is mock_http_client
    assert agent.memory is None  # memory disabled in config
    assert agent.session_id is not None


def test_agent_creates_session_on_init(minimal_config, mock_session_store, mock_http_client):
    """Test that a new session is created when no session_id is provided."""
    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    assert agent.session_id is not None
    assert agent._system_prompt is not None
    assert "test agent" in agent._system_prompt


def test_agent_loads_existing_session(minimal_config, mock_session_store, mock_http_client):
    """Test that an existing session is loaded correctly."""
    # Create a session first
    agent1 = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )
    session_id = agent1.session_id

    # Add a message
    mock_session_store.add_message(session_id, "user", "hello")

    # Load the same session
    agent2 = NovaAgent(
        config=minimal_config,
        session_id=session_id,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    assert agent2.session_id == session_id
    messages = mock_session_store.get_messages(session_id)
    assert len(messages) >= 1


def test_agent_run_no_tool_calls(minimal_config, mock_session_store, mock_http_client):
    """Test a simple run with no tool calls from the model."""
    llm_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "The answer is 42.",
            }
        }]
    }
    mock_http_client.post.return_value = make_mock_response(200, llm_response)

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    result = agent.run("What is the meaning of life?", stream=False)

    assert result == "The answer is 42."
    mock_http_client.post.assert_called_once()
    # Verify the payload includes the user message
    call_args = mock_http_client.post.call_args
    payload = call_args[1]["json"]
    assert any("meaning of life" in str(m.get("content", "")) for m in payload["messages"])


def test_agent_run_with_tool_call(minimal_config, mock_session_store, mock_http_client):
    """Test a run where the model calls a tool."""
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
    mock_http_client.post.side_effect = [
        make_mock_response(200, tool_call_response),
        make_mock_response(200, final_response),
    ]

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    result = agent.run("Run echo hello", stream=False)

    assert result == "The command output was: hello"
    assert mock_http_client.post.call_count == 2


def test_agent_history_truncation(minimal_config, mock_session_store, mock_http_client):
    """Test that conversation history is trimmed when it exceeds the turn limit."""
    minimal_config["budgets"]["conversation_turn_limit"] = 2  # Very small limit for testing

    llm_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "OK",
            }
        }]
    }
    mock_http_client.post.return_value = make_mock_response(200, llm_response)

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
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


def test_agent_execute_tool_call_invalid_json(minimal_config, mock_session_store, mock_http_client):
    """Test that invalid JSON in tool call arguments is handled gracefully."""
    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
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


def test_agent_execute_tool_call_unknown_tool(minimal_config, mock_session_store, mock_http_client):
    """Test that unknown tool names return an error."""
    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
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
    assert "Error" in result


def test_agent_build_system_prompt_with_memory(minimal_config, mock_session_store, mock_http_client, mock_memory_store):
    """Test that system prompt includes memory content when memory is enabled."""
    minimal_config["memory"]["enabled"] = True

    # Add a memory entry
    mock_memory_store.add("User prefers dark mode")

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
        memory_store=mock_memory_store,
    )

    assert agent.memory is not None
    assert agent._system_prompt is not None
    assert "dark mode" in agent._system_prompt


def test_agent_refresh_system_prompt(minimal_config, mock_session_store, mock_http_client, mock_memory_store):
    """Test that _refresh_system_prompt updates the prompt and session."""
    minimal_config["memory"]["enabled"] = True

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
        memory_store=mock_memory_store,
    )

    initial_prompt = agent._system_prompt

    # Add a memory and refresh
    mock_memory_store.add("New fact: user lives in NYC")
    agent._refresh_system_prompt()

    assert agent._system_prompt != initial_prompt or "NYC" in agent._system_prompt
    # Verify session was updated
    info = mock_session_store.get_session_info(agent.session_id)
    assert "NYC" in info.get("system_prompt", "")


def test_agent_max_iterations_limit(minimal_config, mock_session_store, mock_http_client):
    """Test that the agent stops after max_iterations."""
    minimal_config["agent"]["max_iterations"] = 2
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
    mock_http_client.post.return_value = make_mock_response(200, tool_call_response)

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    agent.run("test", stream=False)

    # Should have called the API exactly max_iterations times
    assert mock_http_client.post.call_count == 2


def test_agent_depth_defaults_to_zero(delegation_config, mock_http_client, mock_session_store):
    """Root agents should have depth=0."""
    agent = NovaAgent(
        config=delegation_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )
    assert agent.depth == 0


def test_agent_depth_from_subagent_config(delegation_config, mock_http_client, mock_session_store):
    """Sub-agent config sets depth correctly."""
    delegation_config["_subagent_depth"] = 1
    agent = NovaAgent(
        config=delegation_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )
    assert agent.depth == 1


def test_agent_is_leaf_at_max_depth(delegation_config, mock_http_client, mock_session_store):
    """Agent at max_spawn_depth is a leaf."""
    delegation_config["_subagent_depth"] = 2  # == max_spawn_depth
    agent = NovaAgent(
        config=delegation_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )
    assert agent.is_leaf_agent is True


def test_agent_is_not_leaf_below_max_depth(delegation_config, mock_http_client, mock_session_store):
    """Agent below max_spawn_depth is an orchestrator."""
    delegation_config["_subagent_depth"] = 1  # < max_spawn_depth=2
    agent = NovaAgent(
        config=delegation_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )
    assert agent.is_leaf_agent is False


def test_agent_prompt_mode_respected_for_subagent(delegation_config, mock_http_client, mock_session_store):
    """Sub-agent config with _prompt_mode='minimal' should produce a minimal prompt."""
    delegation_config["_subagent_depth"] = 1
    delegation_config["_prompt_mode"] = "minimal"
    delegation_config["skills"]["enabled"] = True
    delegation_config["skills"]["directory"] = str(Path(tempfile.mkdtemp()))

    agent = NovaAgent(
        config=delegation_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    # Sub-agent should have a minimal prompt (no skills index)
    assert agent._system_prompt is not None
    assert "<skills>" not in (agent._system_prompt or "")
