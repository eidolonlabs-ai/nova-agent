"""Tests for the main agent loop.

Uses dependency injection to mock OpenAI client, session store, and memory store.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from nova.agent import NovaAgent
from nova.tools.registry import discover_builtin_tools


def make_openai_response(content: str = "OK", tool_calls=None) -> MagicMock:
    """Build a mock OpenAI ChatCompletion response."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls
    msg.model_extra = {}
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message = msg
    resp.usage = MagicMock()
    resp.usage.model_dump.return_value = {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    }
    return resp


def test_agent_creation_with_injected_deps(minimal_config, mock_session_store, mock_openai_client):
    """Test that agent accepts injected dependencies."""
    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
    )

    assert agent.session_store is mock_session_store
    assert agent.client is mock_openai_client
    assert agent.wiki is None  # wiki disabled in minimal_config
    assert agent.session_id is not None


def test_agent_creates_session_on_init(minimal_config, mock_session_store, mock_openai_client):
    """Test that a new session is created when no session_id is provided."""
    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
    )

    assert agent.session_id is not None
    assert agent._system_prompt is not None
    assert "test agent" in agent._system_prompt


def test_agent_loads_existing_session(minimal_config, mock_session_store, mock_openai_client):
    """Test that an existing session is loaded correctly."""
    agent1 = NovaAgent(
        config=minimal_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
    )
    session_id = agent1.session_id

    mock_session_store.add_message(session_id, "user", "hello")

    agent2 = NovaAgent(
        config=minimal_config,
        session_id=session_id,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
    )

    assert agent2.session_id == session_id
    messages = mock_session_store.get_messages(session_id)
    assert len(messages) >= 1


def test_agent_run_no_tool_calls(minimal_config, mock_session_store, mock_openai_client):
    """Test a simple run with no tool calls from the model."""
    mock_openai_client.chat.completions.create.return_value = make_openai_response(
        content="The answer is 42."
    )

    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
    )

    result = agent.run("What is the meaning of life?", stream=False)

    assert result == "The answer is 42."
    mock_openai_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
    assert any("meaning of life" in str(m.get("content", "")) for m in call_kwargs["messages"])


def test_agent_run_with_tool_call(minimal_config, mock_session_store, mock_openai_client):
    """Test a run where the model calls a tool."""
    discover_builtin_tools()

    tc_mock = MagicMock()
    tc_mock.model_dump.return_value = {
        "id": "call_123",
        "type": "function",
        "function": {
            "name": "terminal",
            "arguments": json.dumps({"command": "echo hello"}),
        },
    }
    tool_call_response = make_openai_response(content=None, tool_calls=[tc_mock])
    final_response = make_openai_response(content="The command output was: hello")

    mock_openai_client.chat.completions.create.side_effect = [
        tool_call_response,
        final_response,
    ]

    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
    )

    result = agent.run("Run echo hello", stream=False)

    assert result == "The command output was: hello"
    assert mock_openai_client.chat.completions.create.call_count == 2


def test_agent_history_truncation(minimal_config, mock_session_store, mock_openai_client):
    """Test that conversation history is trimmed when it exceeds the turn limit."""
    minimal_config["budgets"]["conversation_turn_limit"] = 2

    mock_openai_client.chat.completions.create.return_value = make_openai_response(content="OK")

    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
    )

    for i in range(10):
        agent.messages.append({"role": "user", "content": f"msg {i}"})
        agent.messages.append({"role": "assistant", "content": f"reply {i}"})

    assert len(agent.messages) == 20

    agent.run("latest message", stream=False)

    assert len(agent.messages) <= 12  # 8 (trimmed) + 2 (new user+assistant)


def test_agent_execute_tool_call_invalid_json(
    minimal_config, mock_session_store, mock_openai_client
):
    """Test that invalid JSON in tool call arguments is handled gracefully."""
    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_openai_client,
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


def test_agent_execute_tool_call_unknown_tool(
    minimal_config, mock_session_store, mock_openai_client
):
    """Test that unknown tool names return an error."""
    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_openai_client,
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


def test_agent_build_system_prompt_with_wiki(
    minimal_config, mock_session_store, mock_openai_client, mock_wiki_store
):
    """Test that system prompt includes wiki content when wiki is enabled."""
    minimal_config["wiki"]["enabled"] = True
    mock_wiki_store.write("Preferences", "User prefers dark mode")

    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
        wiki_memory_store=mock_wiki_store,
    )

    assert agent.wiki is not None
    assert agent._system_prompt is not None
    assert "Preferences" in agent._system_prompt


def test_agent_refresh_system_prompt(
    minimal_config, mock_session_store, mock_openai_client, mock_wiki_store
):
    """Test that _refresh_system_prompt updates the prompt and session."""
    minimal_config["wiki"]["enabled"] = True

    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
        wiki_memory_store=mock_wiki_store,
    )

    initial_prompt = agent._system_prompt
    mock_wiki_store.write("NYC Note", "user lives in NYC")
    agent._refresh_system_prompt()

    assert agent._system_prompt != initial_prompt or "NYC" in agent._system_prompt
    info = mock_session_store.get_session_info(agent.session_id)
    assert "NYC" in info.get("system_prompt", "")


def test_session_resume_refreshes_wiki_content(
    minimal_config, mock_session_store, mock_openai_client, mock_wiki_store
):
    """Session resume rebuilds the system prompt with current wiki state."""
    minimal_config["wiki"]["enabled"] = True

    agent1 = NovaAgent(
        config=minimal_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
        wiki_memory_store=mock_wiki_store,
    )
    session_id = agent1.session_id
    assert "NewFact" not in (agent1._system_prompt or "")

    mock_wiki_store.write("NewFact", "This fact was added between sessions.")

    agent2 = NovaAgent(
        config=minimal_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
        session_id=session_id,
        wiki_memory_store=mock_wiki_store,
    )
    assert "NewFact" in (agent2._system_prompt or "")


def test_agent_max_iterations_limit(minimal_config, mock_session_store, mock_openai_client):
    """Test that the agent stops after max_iterations."""
    minimal_config["agent"]["max_iterations"] = 2
    discover_builtin_tools()

    tc_mock = MagicMock()
    tc_mock.model_dump.return_value = {
        "id": "call_loop",
        "type": "function",
        "function": {
            "name": "terminal",
            "arguments": json.dumps({"command": "echo test"}),
        },
    }
    mock_openai_client.chat.completions.create.return_value = make_openai_response(
        content=None, tool_calls=[tc_mock]
    )

    agent = NovaAgent(
        config=minimal_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
    )

    agent.run("test", stream=False)

    assert mock_openai_client.chat.completions.create.call_count == 2


def test_agent_depth_defaults_to_zero(delegation_config, mock_openai_client, mock_session_store):
    """Root agents should have depth=0."""
    agent = NovaAgent(
        config=delegation_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
    )
    assert agent.depth == 0


def test_agent_depth_from_subagent_config(
    delegation_config, mock_openai_client, mock_session_store
):
    """Sub-agent config sets depth correctly."""
    delegation_config["_subagent_depth"] = 1
    agent = NovaAgent(
        config=delegation_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
    )
    assert agent.depth == 1


def test_agent_is_leaf_at_max_depth(delegation_config, mock_openai_client, mock_session_store):
    """Agent at max_spawn_depth is a leaf."""
    delegation_config["_subagent_depth"] = 2  # == max_spawn_depth
    agent = NovaAgent(
        config=delegation_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
    )
    assert agent.is_leaf_agent is True


def test_agent_is_not_leaf_below_max_depth(
    delegation_config, mock_openai_client, mock_session_store
):
    """Agent below max_spawn_depth is an orchestrator."""
    delegation_config["_subagent_depth"] = 1  # < max_spawn_depth=2
    agent = NovaAgent(
        config=delegation_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
    )
    assert agent.is_leaf_agent is False


def test_agent_prompt_mode_respected_for_subagent(
    delegation_config, mock_openai_client, mock_session_store
):
    """Sub-agent with prompt_mode='minimal' should produce a minimal prompt."""
    delegation_config["_subagent_depth"] = 1
    delegation_config["skills"]["enabled"] = True
    delegation_config["skills"]["directory"] = str(Path(tempfile.mkdtemp()))

    agent = NovaAgent(
        config=delegation_config,
        openai_client=mock_openai_client,
        session_store=mock_session_store,
        prompt_mode="minimal",
    )

    assert agent._system_prompt is not None
    assert "<skills>" not in (agent._system_prompt or "")
