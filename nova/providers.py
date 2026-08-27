"""LLM provider layer — client construction and provider-specific adapters.

Supports OpenAI-compatible endpoints (OpenRouter, OpenAI, Ollama) and native
Anthropic. All provider knowledge lives here so the agent loop stays
provider-agnostic.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from anthropic import Anthropic
from openai import OpenAI

from nova.model_metadata import load_provider_metadata

logger = logging.getLogger(__name__)

PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_OPENAI = "openai"

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def is_anthropic(llm_config: dict) -> bool:
    return llm_config.get("provider", PROVIDER_OPENAI) == PROVIDER_ANTHROPIC


def build_client(llm_config: dict) -> Any:
    """Construct the SDK client for the configured provider."""
    if is_anthropic(llm_config):
        kwargs: dict[str, Any] = {
            "api_key": llm_config["api_key"],
            "default_headers": {
                "anthropic-version": llm_config.get("anthropic_version", "2023-06-01"),
                **llm_config.get("anthropic_headers", {}),
            },
        }
        base_url = llm_config.get("base_url")
        if base_url and base_url != _OPENROUTER_BASE_URL:
            kwargs["base_url"] = base_url
        return Anthropic(**kwargs)
    return OpenAI(
        api_key=llm_config["api_key"],
        base_url=llm_config["base_url"],
        timeout=120.0,
        max_retries=0,
    )


def maybe_load_model_metadata(client: Any, llm_config: dict) -> None:
    """Fetch model context/pricing metadata unless using a native Anthropic client."""
    if not is_anthropic(llm_config):
        load_provider_metadata(client)


def anthropic_messages(
    messages: list[dict[str, Any]],
) -> tuple[str | None, list[dict[str, Any]]]:
    system: str | None = None
    converted: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        if role == "system":
            system = (
                f"{system}\n\n{message.get('content') or ''}"
                if system
                else message.get("content") or ""
            )
            continue
        if role == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": message.get("tool_call_id", ""),
                "content": message.get("content", ""),
            }
            if converted and converted[-1].get("role") == "user":
                existing = converted[-1].get("content")
                if isinstance(existing, list):
                    existing.append(block)
                    continue
            converted.append({"role": "user", "content": [block]})
            continue
        if role == "assistant" and message.get("tool_calls"):
            blocks: list[dict[str, Any]] = []
            if message.get("content"):
                blocks.append({"type": "text", "text": message["content"]})
            for call in message["tool_calls"]:
                function = call.get("function", {})
                try:
                    arguments = json.loads(function.get("arguments", "{}"))
                except (TypeError, json.JSONDecodeError):
                    arguments = {}
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": call.get("id", ""),
                        "name": function.get("name", ""),
                        "input": arguments,
                    }
                )
            converted.append({"role": "assistant", "content": blocks})
            continue
        converted.append({"role": role, "content": message.get("content") or ""})
    return system, converted


def anthropic_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [
        {
            "name": tool["function"]["name"],
            "description": tool["function"].get("description", ""),
            "input_schema": tool["function"].get(
                "parameters", {"type": "object", "properties": {}}
            ),
        }
        for tool in (tools or [])
    ]


def normalize_anthropic_response(response: Any) -> dict[str, Any]:
    content: str | None = None
    tool_calls: list[dict[str, Any]] = []
    text_parts: list[str] = []
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text_parts.append(block.text)
        elif block_type == "tool_use":
            tool_calls.append(
                {
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    },
                }
            )
    if text_parts:
        content = "".join(text_parts)
    usage = getattr(response, "usage", None)
    usage_data = None
    if usage:
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
        usage_data = {
            "prompt_tokens": getattr(usage, "input_tokens", 0) + cache_read + cache_write,
            "completion_tokens": getattr(usage, "output_tokens", 0),
        }
        if cache_read:
            usage_data["cache_read_input_tokens"] = cache_read
        if cache_write:
            usage_data["cache_creation_input_tokens"] = cache_write
    return {
        "choices": [
            {
                "finish_reason": "tool_calls" if tool_calls else "stop",
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls or None,
                },
            }
        ],
        "usage": usage_data,
    }


def call_anthropic(
    client: Any,
    llm_config: dict,
    agent_config: dict,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    stream: bool,
    stream_callback: Callable[[str], None] | None,
) -> dict[str, Any]:
    system, converted = anthropic_messages(messages)
    request: dict[str, Any] = {
        "model": llm_config["model"],
        "messages": converted,
        "max_tokens": llm_config.get("max_tokens", 8192),
        "temperature": agent_config.get("temperature", 0.7),
        "top_p": agent_config.get("top_p", 1.0),
    }
    if system:
        if llm_config.get("prompt_caching", {}).get("enabled") and llm_config.get(
            "prompt_caching", {}
        ).get("cache_system_prompt", True):
            request["system"] = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            request["system"] = system
    anthropic_tool_specs = anthropic_tools(tools)
    if anthropic_tool_specs:
        caching = llm_config.get("prompt_caching", {})
        if caching.get("enabled") and caching.get("cache_tools", True):
            anthropic_tool_specs[-1]["cache_control"] = {"type": "ephemeral"}
        request["tools"] = anthropic_tool_specs
    if stream:
        with client.messages.stream(**request) as stream_response:
            for text in stream_response.text_stream:
                if stream_callback:
                    stream_callback(text)
            return normalize_anthropic_response(stream_response.get_final_message())
    return normalize_anthropic_response(client.messages.create(**request))


def completion_request_kwargs(payload: dict[str, Any], stream: bool = False) -> dict[str, Any]:
    request_kwargs: dict[str, Any] = {
        "model": payload["model"],
        "messages": payload["messages"],
        "temperature": payload.get("temperature", 0.7),
        "top_p": payload.get("top_p", 1.0),
    }
    if payload.get("tools"):
        request_kwargs["tools"] = payload["tools"]
        request_kwargs["tool_choice"] = "auto"
    if "extra_body" in payload:
        request_kwargs["extra_body"] = payload["extra_body"]
    if stream:
        request_kwargs["stream"] = True
        if payload.get("stream_include_usage", True):
            request_kwargs["stream_options"] = {"include_usage": True}
    return request_kwargs


def chat_completion(client: Any, payload: dict[str, Any]) -> dict:
    """Non-streaming OpenAI-compatible completion, normalized to agent shape."""
    request_kwargs = completion_request_kwargs(payload)
    resp = client.chat.completions.create(**request_kwargs)  # type: ignore[call-overload]
    message = resp.choices[0].message
    return {
        "choices": [
            {
                "finish_reason": (
                    resp.choices[0].finish_reason
                    if isinstance(resp.choices[0].finish_reason, str)
                    else None
                ),
                "message": {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": (
                        [tc.model_dump() for tc in message.tool_calls]
                        if message.tool_calls
                        else None
                    ),
                    "reasoning_content": (message.model_extra or {}).get("reasoning_content"),
                },
            }
        ],
        "usage": resp.usage.model_dump() if resp.usage else None,
    }


def stream_response(
    client: Any,
    payload: dict,
    callback: Callable[[str], None] | None = None,
    reasoning_callback: Callable[[str], None] | None = None,
    interrupt_check: Callable[[], bool] | None = None,
) -> dict:
    """Stream a response from an OpenAI-compatible endpoint."""
    full_content = ""
    full_reasoning = ""
    tool_calls: list[dict[str, Any]] = []
    interrupted = False
    finish_reason: str | None = None

    request_kwargs = completion_request_kwargs(payload, stream=True)

    with client.chat.completions.create(**request_kwargs) as stream:  # type: ignore[call-overload]
        usage: dict[str, Any] | None = None
        for chunk in stream:
            if not chunk.choices:
                chunk_usage = getattr(chunk, "usage", None)
                if chunk_usage is not None and hasattr(chunk_usage, "model_dump"):
                    dumped_usage = chunk_usage.model_dump()
                    if isinstance(dumped_usage, dict):
                        usage = dumped_usage
                continue
            chunk_finish_reason = chunk.choices[0].finish_reason
            if isinstance(chunk_finish_reason, str):
                finish_reason = chunk_finish_reason
            delta = chunk.choices[0].delta

            if interrupt_check is not None and interrupt_check():
                logger.info("Stream interrupted by user")
                interrupted = True
                break

            if delta.content:
                full_content += delta.content
                if callback:
                    callback(delta.content)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    index = tc.index
                    while index >= len(tool_calls):
                        tool_calls.append(
                            {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        )
                    if tc.id:
                        tool_calls[index]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls[index]["function"]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls[index]["function"]["arguments"] += tc.function.arguments

            extra = delta.model_extra or {}
            reasoning_chunks: list[str] = []
            for key in ("reasoning", "reasoning_content"):
                value = extra.get(key)
                if isinstance(value, str):
                    reasoning_chunks.append(value)
            details = extra.get("reasoning_details")
            if not reasoning_chunks and isinstance(details, list):
                for detail in details:
                    if isinstance(detail, dict):
                        value = detail.get("text") or detail.get("content")
                        if isinstance(value, str):
                            reasoning_chunks.append(value)
            for reasoning in reasoning_chunks:
                full_reasoning += reasoning
                if reasoning_callback:
                    reasoning_callback(reasoning)

    reasoning_content_value: str | None = full_reasoning if full_reasoning else None
    if not reasoning_content_value and tool_calls:
        reasoning_content_value = ""

    return {
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {
                    "role": "assistant",
                    "content": full_content if full_content else None,
                    "tool_calls": None if interrupted else (tool_calls if tool_calls else None),
                    "reasoning_content": reasoning_content_value,
                },
            }
        ],
        "usage": usage,
    }
