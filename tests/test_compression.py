"""Tests for the context compression module."""

from unittest.mock import MagicMock, patch

from nova.compression import (
    _prepare_for_summary,
    compress_conversation,
    should_compress,
)

# ── _prepare_for_summary ───────────────────────────────────────────────────


def test_prepare_truncates_tool_results():
    messages = [
        {"role": "tool", "content": "x" * 500, "tool_call_id": "1"},
    ]
    result = _prepare_for_summary(messages)
    assert len(result[0]["content"]) <= 215  # 200 + "...[truncated]"
    assert "tool_call_id" not in result[0]


def test_prepare_preserves_short_tool_results():
    messages = [
        {"role": "tool", "content": "short output", "tool_call_id": "1"},
    ]
    result = _prepare_for_summary(messages)
    assert result[0]["content"] == "short output"


def test_prepare_strips_tool_call_arguments():
    messages = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "1",
                    "type": "function",
                    "function": {
                        "name": "terminal",
                        "arguments": '{"command": "ls -la"}',
                    },
                },
            ],
        },
    ]
    result = _prepare_for_summary(messages)
    assert result[0]["tool_calls"][0]["function"]["name"] == "terminal"
    assert result[0]["tool_calls"][0]["function"]["arguments"] == "{}"


def test_prepare_preserves_user_messages():
    messages = [
        {"role": "user", "content": "Hello, how are you?"},
    ]
    result = _prepare_for_summary(messages)
    assert result[0]["content"] == "Hello, how are you?"


# ── should_compress ────────────────────────────────────────────────────────


def test_should_compress_below_threshold():
    messages = [{"role": "user", "content": "hello"}]
    should, tokens = should_compress(
        messages,
        system_prompt="test",
        tools=[],
        context_window=128000,
        threshold_percent=0.40,
        reserve_tokens=15000,
    )
    assert should is False


def test_should_compress_above_threshold():
    # Create a large message list to exceed threshold
    # Threshold = 128000 * 0.40 - 15000 = 36200 tokens
    # At ~4 chars/token, need ~145K chars
    large_content = "x" * 100000
    messages = [
        {"role": "user", "content": large_content},
        {"role": "assistant", "content": large_content},
        {"role": "tool", "content": large_content},
    ]
    should, tokens = should_compress(
        messages,
        system_prompt="test",
        tools=[],
        context_window=128000,
        threshold_percent=0.40,
        reserve_tokens=15000,
    )
    # With 300K chars, should exceed ~36K token threshold
    assert should is True


# ── compress_conversation ──────────────────────────────────────────────────


def test_compress_too_few_messages():
    """Should return None when there aren't enough messages to compress."""
    messages = [
        {"role": "system", "content": "You are a test agent."},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    mock_client = MagicMock()
    result = compress_conversation(
        messages,
        mock_client,
        "test-model",
        "https://api.test",
        "key",
        preserve_recent=6,
    )
    assert result is None


@patch("nova.compression.httpx.Client")
def test_compress_returns_none_on_api_error(mock_client_cls):
    """Should return None when the API call fails."""
    messages = [
        {"role": "system", "content": "You are a test agent."},
        {"role": "user", "content": "task 1"},
        {"role": "assistant", "content": "done 1"},
        {"role": "tool", "content": "result 1"},
        {"role": "user", "content": "task 2"},
        {"role": "assistant", "content": "done 2"},
        {"role": "tool", "content": "result 2"},
        {"role": "user", "content": "task 3"},
        {"role": "assistant", "content": "done 3"},
        {"role": "tool", "content": "result 3"},
        {"role": "user", "content": "task 4"},
        {"role": "assistant", "content": "done 4"},
        {"role": "tool", "content": "result 4"},
        {"role": "user", "content": "task 5"},
        {"role": "assistant", "content": "done 5"},
        {"role": "tool", "content": "result 5"},
        {"role": "user", "content": "task 6"},
        {"role": "assistant", "content": "done 6"},
        {"role": "tool", "content": "result 6"},
        {"role": "user", "content": "task 7"},
        {"role": "assistant", "content": "done 7"},
    ]
    mock_client = MagicMock()
    mock_client.post.side_effect = Exception("API error")

    result = compress_conversation(
        messages,
        mock_client,
        "test-model",
        "https://api.test",
        "key",
        preserve_recent=6,
    )
    assert result is None


def test_compress_system_prompt_included():
    """Verify that the system prompt is included in the compressed output."""
    messages = [
        {"role": "system", "content": "You are a test agent."},
        {"role": "user", "content": "task 1"},
        {"role": "assistant", "content": "done 1"},
        {"role": "tool", "content": "result 1"},
        {"role": "user", "content": "task 2"},
        {"role": "assistant", "content": "done 2"},
        {"role": "tool", "content": "result 2"},
        {"role": "user", "content": "task 3"},
        {"role": "assistant", "content": "done 3"},
        {"role": "tool", "content": "result 3"},
        {"role": "user", "content": "task 4"},
        {"role": "assistant", "content": "done 4"},
        {"role": "tool", "content": "result 4"},
        {"role": "user", "content": "task 5"},
        {"role": "assistant", "content": "done 5"},
        {"role": "tool", "content": "result 5"},
        {"role": "user", "content": "task 6"},
        {"role": "assistant", "content": "done 6"},
        {"role": "tool", "content": "result 6"},
        {"role": "user", "content": "task 7"},
        {"role": "assistant", "content": "done 7"},
    ]
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Summary of tasks 1-7"}}],
    }
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response

    result = compress_conversation(
        messages,
        mock_client,
        "test-model",
        "https://api.test",
        "key",
        preserve_recent=6,
    )

    assert result is not None
    # Should have system prompt + summary + recent messages
    assert any(m.get("content") == "You are a test agent." for m in result)
    assert any("Summary of tasks 1-7" in m.get("content", "") for m in result)
    # Recent messages should be preserved
    assert result[-1]["content"] == "done 7"
