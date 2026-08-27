"""Tests for model metadata."""

from nova.model_metadata import (
    DEFAULT_CONTEXT_WINDOW,
    get_model_context_window,
    get_model_metadata,
    load_provider_metadata,
)


def test_default_context_window():
    assert DEFAULT_CONTEXT_WINDOW == 1_000_000


def test_exact_match():
    load_provider_metadata(
        _Client(
            [
                {"id": "anthropic/claude-sonnet-4-20250514", "context_length": 200_000},
                {"id": "openai/gpt-4o", "context_length": 128_000},
                {"id": "google/gemini-2.5-pro", "context_length": 1_000_000},
            ]
        )
    )
    assert get_model_context_window("anthropic/claude-sonnet-4-20250514") == 200_000
    assert get_model_context_window("openai/gpt-4o") == 128_000
    assert get_model_context_window("google/gemini-2.5-pro") == 1_000_000


def test_partial_match():
    load_provider_metadata(
        _Client([{"id": "anthropic/claude-sonnet-4", "context_length": 200_000}])
    )
    result = get_model_context_window("anthropic/claude-sonnet-4")
    assert result == 200_000


def test_unknown_model_default():
    assert get_model_context_window("unknown/model") == DEFAULT_CONTEXT_WINDOW
    assert get_model_context_window("some-random-model") == DEFAULT_CONTEXT_WINDOW


def test_load_provider_metadata_reads_pricing():
    load_provider_metadata(
        _Client(
            [
                {
                    "id": "test/model",
                    "context_length": 123_456,
                    "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                }
            ]
        )
    )
    metadata = get_model_metadata("test/model")
    assert metadata is not None
    assert metadata.context_window == 123_456
    assert metadata.input_price_per_million == 1.0
    assert metadata.output_price_per_million == 2.0


class _Client:
    def __init__(self, data):
        self.models = self
        self.data = data

    def list(self):
        return {"data": self.data}
