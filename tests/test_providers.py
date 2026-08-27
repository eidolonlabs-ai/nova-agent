"""Tests for the LLM provider layer (nova/providers.py)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from anthropic import Anthropic
from openai import OpenAI

from nova.providers import (
    anthropic_messages,
    anthropic_tools,
    build_client,
    call_anthropic,
    chat_completion,
    completion_request_kwargs,
    is_anthropic,
    maybe_load_model_metadata,
    normalize_anthropic_response,
    stream_response,
)


def test_is_anthropic_defaults_to_openai():
    assert is_anthropic({"provider": "openai"}) is False
    assert is_anthropic({}) is False
    assert is_anthropic({"provider": "anthropic"}) is True


def test_build_client_openai_compatible(minimal_config):
    client = build_client(minimal_config["llm"])
    assert isinstance(client, OpenAI)
    assert "openrouter.ai/api/v1" in str(client.base_url)


def test_build_client_anthropic_default_base_url():
    llm_config = {
        "provider": "anthropic",
        "api_key": "sk-ant-test",
        "base_url": "https://openrouter.ai/api/v1",
    }
    client = build_client(llm_config)
    assert isinstance(client, Anthropic)
    # OpenRouter default is not forwarded to the native Anthropic SDK
    assert client.base_url is None or "openrouter" not in str(client.base_url)


def test_build_client_anthropic_custom_base_url():
    llm_config = {
        "provider": "anthropic",
        "api_key": "sk-ant-test",
        "base_url": "https://api.anthropic.com",
        "anthropic_version": "2023-06-01",
    }
    client = build_client(llm_config)
    assert isinstance(client, Anthropic)
    assert "api.anthropic.com" in str(client.base_url)


def test_maybe_load_model_metadata_skips_anthropic(minimal_config, monkeypatch):
    called = []
    monkeypatch.setattr("nova.providers.load_provider_metadata", lambda client: called.append(1))
    maybe_load_model_metadata(MagicMock(), {**minimal_config["llm"], "provider": "anthropic"})
    assert called == []


def test_maybe_load_model_metadata_loads_openai(minimal_config, monkeypatch):
    called = []
    monkeypatch.setattr("nova.providers.load_provider_metadata", lambda client: called.append(1))
    maybe_load_model_metadata(MagicMock(), minimal_config["llm"])
    assert called == [1]


def test_anthropic_messages_translates_system_tool_and_usage_blocks():
    system, messages = anthropic_messages(
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
    assert messages[-1]["content"][0]["tool_use_id"] == "tool_1"


def test_anthropic_tools_converts_function_specs():
    result = anthropic_tools(
        [
            {
                "type": "function",
                "function": {
                    "name": "terminal",
                    "description": "Run a command",
                    "parameters": {"type": "object"},
                },
            }
        ]
    )
    assert result == [
        {"name": "terminal", "description": "Run a command", "input_schema": {"type": "object"}}
    ]


def test_anthropic_tools_empty_input():
    assert anthropic_tools(None) == []
    assert anthropic_tools([]) == []


def test_normalize_anthropic_response_text_and_tool_use():
    response = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="I will do that."),
            SimpleNamespace(
                type="tool_use", id="tool_1", name="terminal", input={"command": "pwd"}
            ),
        ],
        usage=SimpleNamespace(input_tokens=12, output_tokens=8),
    )
    normalized = normalize_anthropic_response(response)
    assert normalized["usage"] == {"prompt_tokens": 12, "completion_tokens": 8}
    assert normalized["choices"][0]["finish_reason"] == "tool_calls"
    tool_call = normalized["choices"][0]["message"]["tool_calls"][0]
    assert tool_call["function"]["name"] == "terminal"
    assert tool_call["function"]["arguments"] == '{"command": "pwd"}'


def test_normalize_anthropic_response_counts_cache_tokens():
    response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="OK")],
        usage=SimpleNamespace(
            input_tokens=5,
            output_tokens=3,
            cache_read_input_tokens=100,
            cache_creation_input_tokens=50,
        ),
    )
    usage = normalize_anthropic_response(response)["usage"]
    assert usage["prompt_tokens"] == 155
    assert usage["cache_read_input_tokens"] == 100
    assert usage["cache_creation_input_tokens"] == 50


def test_call_anthropic_shapes_request(minimal_config):
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="OK")],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
    )
    llm_config = {**minimal_config["llm"], "provider": "anthropic"}
    result = call_anthropic(
        client,
        llm_config,
        minimal_config["agent"],
        [{"role": "system", "content": "Be useful."}, {"role": "user", "content": "Hi"}],
        tools=None,
        stream=False,
        stream_callback=None,
    )
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["system"] == "Be useful."
    assert kwargs["max_tokens"] == 8192
    assert kwargs["temperature"] == 0.7
    assert result["choices"][0]["message"]["content"] == "OK"


def test_call_anthropic_prompt_caching_marks_blocks(minimal_config):
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="OK")],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
    )
    llm_config = {
        **minimal_config["llm"],
        "provider": "anthropic",
        "prompt_caching": {"enabled": True},
    }
    call_anthropic(
        client,
        llm_config,
        minimal_config["agent"],
        [{"role": "system", "content": "Stable"}, {"role": "user", "content": "Hi"}],
        tools=[{"type": "function", "function": {"name": "x", "parameters": {}}}],
        stream=False,
        stream_callback=None,
    )
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kwargs["tools"][0]["cache_control"] == {"type": "ephemeral"}


def test_call_anthropic_streaming(minimal_config):
    class MockTextStream:
        text_stream = ["Hello", " world"]

    class MockStream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get_final_message(self):
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Hello world")],
                usage=SimpleNamespace(input_tokens=1, output_tokens=1),
            )

    client = MagicMock()
    stream_cm = MockStream()
    stream_cm.text_stream = iter(["Hello", " world"])
    client.messages.stream.return_value = stream_cm
    received = []

    result = call_anthropic(
        client,
        {**minimal_config["llm"], "provider": "anthropic"},
        minimal_config["agent"],
        [{"role": "user", "content": "Hi"}],
        tools=None,
        stream=True,
        stream_callback=received.append,
    )

    assert received == ["Hello", " world"]
    assert result["choices"][0]["message"]["content"] == "Hello world"


def test_completion_request_kwargs_plain(minimal_config):
    payload = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Hi"}],
        "temperature": 0.7,
        "top_p": 1.0,
        "stream_include_usage": True,
    }
    kwargs = completion_request_kwargs(payload)
    assert kwargs["model"] == "test-model"
    assert "tools" not in kwargs
    assert "stream" not in kwargs


def test_completion_request_kwargs_stream_and_tools():
    payload = {
        "model": "test-model",
        "messages": [],
        "temperature": 0.7,
        "top_p": 1.0,
        "stream_include_usage": False,
        "tools": [{"type": "function"}],
        "extra_body": {"reasoning": {"enabled": True}},
    }
    kwargs = completion_request_kwargs(payload, stream=True)
    assert kwargs["stream"] is True
    assert kwargs["tool_choice"] == "auto"
    assert "stream_options" not in kwargs
    assert kwargs["extra_body"] == {"reasoning": {"enabled": True}}


def test_chat_completion_normalizes_response(minimal_config, mock_openai_client):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].finish_reason = "stop"
    msg = resp.choices[0].message
    msg.content = "Hello"
    msg.tool_calls = None
    msg.model_extra = {}
    resp.usage.model_dump.return_value = {"prompt_tokens": 1, "completion_tokens": 1}
    mock_openai_client.chat.completions.create.return_value = resp

    result = chat_completion(
        mock_openai_client,
        {"model": "test-model", "messages": [], "temperature": 0.7, "top_p": 1.0},
    )

    assert result["choices"][0]["message"]["content"] == "Hello"
    assert result["usage"] == {"prompt_tokens": 1, "completion_tokens": 1}


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


def make_usage_chunk(usage: dict) -> MagicMock:
    chunk = MagicMock()
    chunk.choices = []
    chunk.usage.model_dump.return_value = usage
    return chunk


def test_stream_response_accumulates_text(mock_openai_client):
    mock_openai_client.chat.completions.create.return_value = make_mock_stream(
        make_text_chunk("Hello"), make_text_chunk(" world")
    )
    received = []
    result = stream_response(
        mock_openai_client,
        {"model": "test-model", "messages": [], "temperature": 0.7, "top_p": 1.0},
        callback=received.append,
    )
    assert received == ["Hello", " world"]
    assert result["choices"][0]["message"]["content"] == "Hello world"


def test_stream_response_interrupt_stops_early(mock_openai_client):
    mock_openai_client.chat.completions.create.return_value = make_mock_stream(
        make_text_chunk("Hello"), make_text_chunk(" world")
    )
    result = stream_response(
        mock_openai_client,
        {"model": "test-model", "messages": [], "temperature": 0.7, "top_p": 1.0},
        interrupt_check=lambda: True,
    )
    assert result["choices"][0]["message"]["content"] is None


def test_stream_response_captures_usage(mock_openai_client):
    mock_openai_client.chat.completions.create.return_value = make_mock_stream(
        make_text_chunk("answer"),
        make_usage_chunk({"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16}),
    )
    result = stream_response(
        mock_openai_client,
        {"model": "test-model", "messages": [], "temperature": 0.7, "top_p": 1.0},
    )
    assert result["usage"]["prompt_tokens"] == 12
    call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["stream_options"] == {"include_usage": True}


def test_stream_response_empty_stream(mock_openai_client):
    mock_openai_client.chat.completions.create.return_value = make_mock_stream()
    result = stream_response(
        mock_openai_client,
        {"model": "test-model", "messages": [], "temperature": 0.7, "top_p": 1.0},
    )
    assert result["choices"][0]["message"]["content"] is None
