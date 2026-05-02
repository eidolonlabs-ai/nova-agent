"""Model metadata — context window sizes for common OpenRouter models.

Used to calibrate context compression thresholds and history limits.
"""

# Known context windows for popular models (tokens)
# Source: OpenRouter model pages, provider documentation
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    # Anthropic
    "anthropic/claude-sonnet-4-20250514": 200_000,
    "anthropic/claude-opus-4-20250514": 200_000,
    "anthropic/claude-3-5-sonnet-20241022": 200_000,
    "anthropic/claude-3-5-haiku-20241022": 200_000,
    # OpenAI
    "openai/gpt-4o": 128_000,
    "openai/gpt-4o-mini": 128_000,
    "openai/o1": 200_000,
    "openai/o3-mini": 200_000,
    # Google
    "google/gemini-2.5-pro": 1_000_000,
    "google/gemini-2.0-flash-exp:free": 1_000_000,
    "google/gemini-2.0-flash": 1_000_000,
    # Qwen
    "qwen/qwen3.6-flash": 131_072,
    "qwen/qwen3-235b-a22b": 131_072,
    "qwen/qwen-plus": 131_072,
    # Meta
    "meta-llama/llama-3.3-70b-instruct": 131_072,
    "meta-llama/llama-3.1-405b-instruct": 131_072,
    # Mistral
    "mistralai/mistral-large-2411": 131_000,
    "mistralai/mistral-small-2503": 131_000,
    # DeepSeek
    "deepseek/deepseek-chat": 128_000,
    "deepseek/deepseek-r1": 128_000,
}

# Default context window when model is not in the lookup table
DEFAULT_CONTEXT_WINDOW = 128_000


def get_model_context_window(model: str) -> int:
    """Return the context window size for a model, or the default."""
    # Exact match
    if model in MODEL_CONTEXT_WINDOWS:
        return MODEL_CONTEXT_WINDOWS[model]

    # Partial match (e.g., user specifies a variant)
    model_lower = model.lower()
    for key, value in MODEL_CONTEXT_WINDOWS.items():
        if key.lower() in model_lower or model_lower in key.lower():
            return value

    return DEFAULT_CONTEXT_WINDOW
