"""Token estimation utilities.

Uses tiktoken for accurate token counting when available,
falls back to character-based estimation.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Rough chars-per-token estimate for fallback
_CHARS_PER_TOKEN = 4

# Module-level encoder cache — initialised once, reused for every estimate call
_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            import tiktoken
            _encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            pass
    return _encoder


def estimate_tokens(text: str) -> int:
    """Estimate token count for a string.

    Uses tiktoken (cl100k_base) when available, falls back to
    character-based estimation.
    """
    if not text:
        return 0

    enc = _get_encoder()
    if enc is not None:
        try:
            return len(enc.encode(text))
        except Exception:
            pass
    return len(text) // _CHARS_PER_TOKEN


def estimate_messages_tokens(messages: list[dict[str, Any]]) -> int:
    """Estimate total tokens for a message list."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    total += estimate_tokens(part.get("text", "") or "")
                elif isinstance(part, str):
                    total += estimate_tokens(part)
        # Add overhead for message structure
        total += 4  # role + content framing
    return total


def estimate_tool_tokens(tools: list[dict[str, Any]]) -> int:
    """Estimate tokens for tool schema definitions."""
    import json

    total = 0
    for tool in tools:
        total += estimate_tokens(json.dumps(tool, ensure_ascii=False))
    return total


def estimate_system_prompt_tokens(system_prompt: str) -> int:
    """Estimate tokens for the system prompt."""
    return estimate_tokens(system_prompt)


def estimate_total_request_tokens(
    messages: list[dict[str, Any]],
    system_prompt: str = "",
    tools: list[dict[str, Any]] | None = None,
) -> int:
    """Estimate total tokens for an API request."""
    total = estimate_tokens(system_prompt)
    total += estimate_messages_tokens(messages)
    if tools:
        total += estimate_tool_tokens(tools)
    return total
