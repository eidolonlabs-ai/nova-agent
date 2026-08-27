"""Model metadata loaded from an OpenAI-compatible provider endpoint."""

from dataclasses import dataclass
from typing import Any

DEFAULT_CONTEXT_WINDOW = 1_000_000


@dataclass(frozen=True)
class ModelMetadata:
    context_window: int | None = None
    input_price_per_million: float | None = None
    output_price_per_million: float | None = None
    cache_read_price_per_million: float | None = None
    cache_write_price_per_million: float | None = None


_MODEL_METADATA: dict[str, ModelMetadata] = {}


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _price(pricing: Any, name: str) -> float | None:
    try:
        value = float(_value(pricing, name))
        return value * 1_000_000 if value >= 0 else None
    except (TypeError, ValueError):
        return None


def load_provider_metadata(client: Any) -> dict[str, ModelMetadata]:
    """Load model context and pricing metadata from ``client.models.list()``.

    Metadata is optional because some compatible providers do not implement the
    models endpoint or return incomplete records. In either case, callers retain
    safe defaults and the error is intentionally non-fatal.
    """
    _MODEL_METADATA.clear()
    try:
        response = client.models.list()
        records = _value(response, "data", []) or []
    except Exception:
        return {}

    loaded: dict[str, ModelMetadata] = {}
    for record in records:
        model_id = _value(record, "id")
        if not isinstance(model_id, str) or not model_id:
            continue

        context = _value(record, "context_length")
        pricing = _value(record, "pricing", {}) or {}
        try:
            context_value = int(context) if context is not None and int(context) > 0 else None
        except (TypeError, ValueError):
            context_value = None

        loaded[model_id] = ModelMetadata(
            context_window=context_value,
            input_price_per_million=_price(pricing, "prompt"),
            output_price_per_million=_price(pricing, "completion"),
            cache_read_price_per_million=_price(pricing, "cache_read"),
            cache_write_price_per_million=_price(pricing, "cache_write"),
        )

    _MODEL_METADATA.update(loaded)
    return loaded


def get_model_metadata(model: str) -> ModelMetadata | None:
    """Return exact or partial-match metadata for a model identifier."""
    if model in _MODEL_METADATA:
        return _MODEL_METADATA[model]
    model_lower = model.lower()
    for key, value in _MODEL_METADATA.items():
        if key.lower() in model_lower or model_lower in key.lower():
            return value
    return None


def get_model_context_window(model: str) -> int:
    """Return the provider-reported context window, or a 1M-token default."""
    metadata = get_model_metadata(model)
    return (
        metadata.context_window if metadata and metadata.context_window else DEFAULT_CONTEXT_WINDOW
    )
