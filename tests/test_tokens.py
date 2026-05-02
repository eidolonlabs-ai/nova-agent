"""Tests for token estimation utilities."""

from nova.tokens import estimate_messages_tokens, estimate_tokens


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_estimate_tokens_basic():
    # "hello world" should be 2 tokens with tiktoken
    tokens = estimate_tokens("hello world")
    assert tokens > 0


def test_estimate_messages_tokens():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    tokens = estimate_messages_tokens(messages)
    assert tokens > 0


def test_estimate_tokens_multimodal():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's in this image?"},
                {"type": "image_url", "image_url": {"url": "https://example.com/img.jpg"}},
            ],
        }
    ]
    tokens = estimate_messages_tokens(messages)
    assert tokens > 0
