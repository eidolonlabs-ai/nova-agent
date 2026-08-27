"""Tests for the native Anthropic provider adapter."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from nova.agent import NovaAgent


def test_anthropic_messages_translate_system_and_tool_blocks():
    system, messages = NovaAgent._anthropic_messages(
        [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Run it."},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "tool_1",
                        "function": {"name": "terminal", "arguments": '{"command":"pwd"}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "tool_1", "content": "/tmp"},
        ]
    )

    assert system == "Be concise."
    assert messages[-2]["content"][0]["type"] == "tool_use"
    assert messages[-1]["content"][0]["type"] == "tool_result"
    assert messages[-2]["content"][0]["input"] == {"command": "pwd"}


def test_anthropic_call_normalizes_text_and_tool_use(minimal_config, mock_session_store):
    config = {**minimal_config, "llm": {**minimal_config["llm"], "provider": "anthropic"}}
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="I will do that."),
            SimpleNamespace(
                type="tool_use", id="tool_1", name="terminal", input={"command": "pwd"}
            ),
        ],
        usage=SimpleNamespace(input_tokens=12, output_tokens=8),
    )
    agent = NovaAgent(config=config, openai_client=client, session_store=mock_session_store)

    response = agent._call_llm(
        [{"role": "system", "content": "Be useful."}, {"role": "user", "content": "Do it."}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "terminal",
                    "description": "Run a command",
                    "parameters": {"type": "object"},
                },
            }
        ],
        stream=False,
    )

    assert response["usage"] == {"prompt_tokens": 12, "completion_tokens": 8}
    assert response["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "terminal"
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["system"] == "Be useful."
    assert kwargs["max_tokens"] == 8192
    assert kwargs["tools"][0]["input_schema"] == {"type": "object"}


def test_anthropic_prompt_caching_marks_stable_blocks(minimal_config, mock_session_store):
    config = {
        **minimal_config,
        "llm": {
            **minimal_config["llm"],
            "provider": "anthropic",
            "prompt_caching": {"enabled": True},
        },
    }
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="OK")],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
    )
    agent = NovaAgent(config=config, openai_client=client, session_store=mock_session_store)
    agent._call_llm(
        [{"role": "system", "content": "Stable instructions"}, {"role": "user", "content": "Hi"}],
        tools=[{"type": "function", "function": {"name": "x", "parameters": {}}}],
        stream=False,
    )
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kwargs["tools"][0]["cache_control"] == {"type": "ephemeral"}
