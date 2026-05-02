"""Tests for model metadata."""

from nova.model_metadata import DEFAULT_CONTEXT_WINDOW, get_model_context_window


def test_exact_match():
    assert get_model_context_window("anthropic/claude-sonnet-4-20250514") == 200_000
    assert get_model_context_window("openai/gpt-4o") == 128_000
    assert get_model_context_window("google/gemini-2.5-pro") == 1_000_000


def test_partial_match():
    # Variant of a known model
    result = get_model_context_window("anthropic/claude-sonnet-4")
    assert result == 200_000


def test_unknown_model_default():
    assert get_model_context_window("unknown/model") == DEFAULT_CONTEXT_WINDOW
    assert get_model_context_window("some-random-model") == DEFAULT_CONTEXT_WINDOW
