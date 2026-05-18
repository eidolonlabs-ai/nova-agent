"""Context compression — LLM-based summarization of older messages.

Tier 2 of the compaction strategy (after microcompact):
1. Microcompact — strip old tool content (cheap, no LLM call)
2. Context compression — LLM summarizes older messages
3. Full session reset — user starts a new session

Design: summarizes older messages while preserving tool call/result
pairs and recent context. The summary is injected as a single
system-level message.
"""

import logging
from typing import Any

from openai import OpenAI

from nova.tokens import estimate_messages_tokens

logger = logging.getLogger(__name__)

# How many recent messages to always preserve (not summarize)
_DEFAULT_PRESERVE_RECENT = 6

# System prompt for the summarization model
_COMPACT_SYSTEM_PROMPT = (
    "You are summarizing a conversation between a user and an AI assistant. "
    "Produce a concise summary that preserves: "
    "1. The user's original goals and requests "
    "2. Key decisions made and conclusions reached "
    "3. Important file paths, code snippets, or technical details mentioned "
    "4. Any errors encountered and how they were resolved "
    "5. The current state of work and what remains to be done "
    "Be concise but thorough. Use bullet points. Do not include conversational filler. "
    "Focus on facts and actionable information."
)


def compress_conversation(
    messages: list[dict[str, Any]],
    openai_client: OpenAI,
    model: str,
    preserve_recent: int = _DEFAULT_PRESERVE_RECENT,
    temperature: float = 0.0,
) -> list[dict[str, Any]] | None:
    """Compress older messages using LLM summarization.

    Args:
        messages: Full message list (system + conversation).
        openai_client: OpenAI client for API calls.
        model: Model to use for summarization.
        preserve_recent: Number of recent messages to preserve fully.
        temperature: Temperature for summarization (0.0 = deterministic).

    Returns:
        New message list with older messages replaced by a summary,
        or None if compression is not possible (too few messages).
    """
    # Skip system prompt for counting
    conversation = [m for m in messages if m.get("role") != "system"]

    if len(conversation) <= preserve_recent + 2:
        # Not enough messages to compress (need at least some older + recent)
        return None

    # Split into older (summarize) and recent (preserve)
    older = conversation[:-preserve_recent]
    recent = conversation[-preserve_recent:]

    # Build messages for summarization
    # Filter out tool results that are already stripped (from microcompact)
    older_for_summary = _prepare_for_summary(older)

    if not older_for_summary:
        return None

    summary_messages = [
        {"role": "system", "content": _COMPACT_SYSTEM_PROMPT},
        *older_for_summary,
        {"role": "user", "content": "Summarize the conversation above."},
    ]

    try:
        response = openai_client.chat.completions.create(  # type: ignore[call-overload]
            model=model,
            messages=summary_messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=2000,
        )
        summary = response.choices[0].message.content or ""

        if not summary:
            logger.warning("Compression returned empty summary — falling back to microcompact")
            from nova.microcompact import microcompact_messages

            return microcompact_messages(messages)

        # Build new message list: system prompt + summary + recent
        system_msg = next((m for m in messages if m.get("role") == "system"), None)
        new_messages = []
        if system_msg:
            new_messages.append(system_msg)

        # Inject summary as a tool-like message
        new_messages.append(
            {
                "role": "system",
                "content": f"[Previous conversation summary]\n{summary}",
            }
        )

        new_messages.extend(recent)

        original_tokens = estimate_messages_tokens(older)
        new_tokens = estimate_messages_tokens(new_messages)
        savings = original_tokens - new_tokens

        logger.info(
            "Context compression: %d tokens → %d tokens (saved %d, "
            "summarized %d messages, preserved %d)",
            original_tokens,
            new_tokens,
            savings,
            len(older),
            len(recent),
        )

        return new_messages

    except Exception as e:
        logger.error("Context compression failed: %s", e)
        return None


def _prepare_for_summary(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Prepare older messages for summarization.

    - Keep user and assistant messages intact
    - Truncate tool results to first 200 chars (summary doesn't need full output)
    - Remove tool_call_id references (not needed for summary)
    - Preserve tool call names (useful context)
    """
    result = []
    for msg in messages:
        role = msg.get("role", "")
        new_msg = dict(msg)

        if role == "tool":
            # Truncate tool content for summarization
            content = msg.get("content", "")
            if len(content) > 200:
                new_msg["content"] = content[:200] + "...[truncated]"
            # Remove tool_call_id — not needed for summary
            new_msg.pop("tool_call_id", None)

        elif role == "assistant" and "tool_calls" in msg:
            # Keep tool call names but strip arguments
            truncated_calls = []
            for tc in msg.get("tool_calls", []):
                truncated_calls.append(
                    {
                        "id": tc.get("id", ""),
                        "type": tc.get("type", "function"),
                        "function": {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": "{}",
                        },
                    }
                )
            new_msg["tool_calls"] = truncated_calls

        result.append(new_msg)

    return result


def should_compress(
    messages: list[dict[str, Any]],
    system_prompt: str,
    tools: list[dict],
    context_window: int,
    threshold_percent: float,
    reserve_tokens: int,
) -> tuple[bool, int]:
    """Check if context compression should be triggered.

    Returns:
        (should_compress, total_tokens)
    """
    from nova.tokens import estimate_total_request_tokens

    total_tokens = estimate_total_request_tokens(
        messages,
        system_prompt=system_prompt,
        tools=tools,
    )

    threshold = int(context_window * threshold_percent) - reserve_tokens
    return total_tokens >= threshold, total_tokens
