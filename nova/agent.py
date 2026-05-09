"""Main agent loop.

Handles the conversation loop with tool calling, streaming,
context compression, and session management.
"""

import json
import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import httpx

from nova.compression import compress_conversation
from nova.config import ensure_nova_home, load_config
from nova.cost_tracker import CostTracker, extract_usage_from_response
from nova.hooks import (
    EVENT_POST_LLM_CALL,
    EVENT_POST_TOOL_CALL,
    EVENT_PRE_LLM_CALL,
    EVENT_PRE_TOOL_CALL,
    EVENT_SESSION_START,
    hooks,
)
from nova.memory import MemoryStore
from nova.microcompact import microcompact_messages
from nova.model_metadata import get_model_context_window
from nova.permissions import PermissionChecker, build_permission_checker
from nova.prompt import build_system_prompt
from nova.retry import retry_with_backoff
from nova.session import SessionStore
from nova.tokens import (
    estimate_messages_tokens,
    estimate_tokens,
    estimate_tool_tokens,
    estimate_total_request_tokens,
)
from nova.tools.registry import discover_builtin_tools, registry

logger = logging.getLogger(__name__)


def _log_api_400_error(payload: dict, response_text: str) -> None:
    """Log API 400 error with safe payload inspection (no secrets)."""
    safe_payload = {
        "model": payload.get("model"),
        "message_count": len(payload.get("messages", [])),
        "has_tools": "tools" in payload,
    }
    logger.error("API 400 error. Request: %s", json.dumps(safe_payload))
    logger.error("Response: %s", response_text[:1000])


class NovaAgent:
    """Main agent class with explicit token budgets and smart context management."""

    def __init__(
        self,
        config: dict | None = None,
        session_id: str | None = None,
        http_client: httpx.Client | None = None,
        session_store: SessionStore | None = None,
        memory_store: MemoryStore | None = None,
    ):
        self.config = config or load_config()
        self.session_id = session_id
        self.messages: list[dict[str, Any]] = []
        self._system_prompt: str | None = None
        self._cached_system_prompt: str | None = None
        self._interrupt_check: Callable[[], bool] | None = None
        # Token estimate cache: hash(content) → token_count (bounded to 2048 entries)
        self._token_cache: dict[int, int] = {}

        # Initialize components
        ensure_nova_home()

        # Session store (injectable for testing)
        if session_store is not None:
            self.session_store = session_store
        else:
            session_dir = Path(self.config["session"]["directory"]).expanduser()
            self.session_store = SessionStore(session_dir / "sessions.db")

        # Memory store (injectable for testing)
        if memory_store is not None:
            self.memory: MemoryStore | None = memory_store
        elif self.config["memory"]["enabled"]:
            memory_file = Path(self.config["memory"]["file"]).expanduser()
            self.memory = MemoryStore(
                memory_file,
                max_entries=self.config["memory"]["max_entries"],
            )
        else:
            self.memory = None

        # HTTP client (injectable for testing)
        self._owns_client = http_client is None
        if http_client is not None:
            self.client = http_client
        else:
            openrouter_config = self.config["openrouter"]
            self.client = httpx.Client(
                base_url=openrouter_config["base_url"],
                headers={
                    "Authorization": f"Bearer {openrouter_config['api_key']}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://nova-agent.local",
                    "X-Title": "Nova Agent",
                },
                timeout=120.0,
            )

        # Discover tools (pass config so delegation tool can be gated)
        # Must happen before _create_session so system prompt includes tool summaries
        discover_builtin_tools(self.config)

        try:
            # Sub-agent depth tracking
            self.depth: int = self.config.get("_subagent_depth", 0)
            max_spawn_depth = self.config.get("delegation", {}).get("max_spawn_depth", 2)
            self.is_leaf_agent: bool = self.depth >= max_spawn_depth

            # Permission checker
            self.permission_checker: PermissionChecker = build_permission_checker(self.config)

            # Cost tracker
            cost_cfg = self.config.get("cost_tracking", {})
            self.cost_tracker: CostTracker | None = None
            if cost_cfg.get("enabled", True):
                self.cost_tracker = CostTracker(model=self.config["openrouter"]["model"])

            # Create or load session (tools discovered above, so _build_system_prompt
            # will include tool summaries from the start)
            if self.session_id:
                self._load_session()
            else:
                self._create_session()

            # Fire session_start hook
            hooks.emit(EVENT_SESSION_START, session_id=self.session_id, config=self.config)
        except Exception:
            # Clean up HTTP client if init fails after creating it
            self.close()
            raise

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._owns_client and hasattr(self.client, "close"):
            self.client.close()

    def _create_session(self):
        """Create a new session."""
        self.session_id = self.session_store.create_session(
            model=self.config["openrouter"]["model"],
        )
        self._build_system_prompt()
        self.session_store.update_system_prompt(self.session_id, self._system_prompt or "")

    def _load_session(self):
        """Load an existing session."""
        if not self.session_id:
            self._create_session()
            return

        info = self.session_store.get_session_info(self.session_id)
        if info:
            # Load recent messages only — respect conversation turn limit
            turn_limit = self.config["budgets"].get("conversation_turn_limit", 15)
            self.messages = self.session_store.get_messages(
                self.session_id,
                limit=turn_limit * 4,  # ~4 msgs per turn (user+assistant+tool pairs)
            )
            self._system_prompt = info.get("system_prompt")
            self._cached_system_prompt = self._system_prompt
        else:
            logger.warning("Session %s not found, creating new", self.session_id)
            self._create_session()

    def _build_system_prompt(self, mode: str | None = None):
        """Build the system prompt with budget enforcement.

        The mode is resolved in priority order:
        1. Explicit ``mode`` argument (used by tests / refresh calls)
        2. ``config["_prompt_mode"]`` — set by sub-agent config builder
        3. ``"full"`` — default for root agents
        """
        resolved_mode = mode or self.config.get("_prompt_mode", "full")
        memory_content = None
        if self.memory:
            memory_content = self.memory.format_for_prompt()

        self._system_prompt = build_system_prompt(
            config=self.config,
            mode=resolved_mode,
            memory_content=memory_content,
        )
        self._cached_system_prompt = self._system_prompt

    def _refresh_system_prompt(self, mode: str = "full"):
        """Rebuild the system prompt (e.g., after memory changes)."""
        self._build_system_prompt(mode=mode)
        if self.session_id:
            self.session_store.update_system_prompt(
                self.session_id,
                self._system_prompt or "",
            )

    def _call_llm(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        stream: bool = False,
        stream_callback: Callable[[str], None] | None = None,
    ) -> dict:
        """Make an API call to OpenRouter with retry logic."""
        # Fire pre_llm_call hook
        hooks.emit(EVENT_PRE_LLM_CALL, messages=messages, tools=tools)

        openrouter_config = self.config["openrouter"]
        agent_config = self.config["agent"]
        retry_cfg = self.config.get("retry", {})

        payload = {
            "model": openrouter_config["model"],
            "messages": messages,
            "temperature": agent_config.get("temperature", 0.7),
            "top_p": agent_config.get("top_p", 1.0),
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        else:
            # Some models reject empty tools array
            pass

        max_retries = retry_cfg.get("max_retries", 3)
        base_delay = retry_cfg.get("base_delay", 1.0)
        max_delay = retry_cfg.get("max_delay", 60.0)

        if stream:
            response_data: dict = retry_with_backoff(
                self._stream_response,
                payload,
                stream_callback,
                getattr(self, "_reasoning_callback", None),
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
            )
        else:

            def _do_post() -> dict:
                http_response = self.client.post("/chat/completions", json=payload)
                if http_response.status_code == 400:
                    _log_api_400_error(payload, http_response.text)
                http_response.raise_for_status()
                return http_response.json()

            response_data = retry_with_backoff(
                _do_post,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
            )

        # Track cost from response
        if self.cost_tracker:
            usage = extract_usage_from_response(response_data)
            self.cost_tracker.add_usage(**usage)

        # Fire post_llm_call hook
        hooks.emit(EVENT_POST_LLM_CALL, response=response_data)

        return response_data

    def _stream_response(
        self,
        payload: dict,
        callback: Callable[[str], None] | None = None,
        reasoning_callback: Callable[[str], None] | None = None,
    ) -> dict:
        """Stream a response from the API."""
        payload["stream"] = True

        full_content = ""
        tool_calls: list[dict[str, Any]] = []

        with self.client.stream("POST", "/chat/completions", json=payload) as response:
            if response.status_code == 400:
                body = response.read().decode()
                _log_api_400_error(payload, body)
                raise httpx.HTTPStatusError(
                    f"Bad Request: {body[:500]}",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
            _last_delta_time = time.monotonic()
            _watchdog_timeout = 30.0  # seconds with no delta before giving up
            for line in response.iter_lines():
                # Streaming watchdog: bail if no data for 30s
                if time.monotonic() - _last_delta_time > _watchdog_timeout:
                    logger.warning(
                        "Stream watchdog: no data for %.0fs, aborting", _watchdog_timeout
                    )
                    break

                # Interrupt check: Ctrl+C was pressed
                _ic = getattr(self, "_interrupt_check", None)
                if _ic is not None and _ic():
                    logger.info("Stream interrupted by user")
                    break

                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                _last_delta_time = time.monotonic()  # reset watchdog on each valid chunk
                delta = data.get("choices", [{}])[0].get("delta", {})

                # Handle reasoning content (OpenRouter sends this separately)
                reasoning = delta.get("reasoning")
                if reasoning and reasoning_callback:
                    reasoning_callback(reasoning)

                # Handle text content
                content = delta.get("content")
                if content:
                    full_content += content
                    if callback:
                        callback(content)

                # Handle tool calls
                if delta.get("tool_calls"):
                    for tc in delta["tool_calls"]:
                        index = tc.get("index", 0)
                        if index >= len(tool_calls):
                            tool_calls.append(
                                {
                                    "id": tc.get("id", ""),
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            )
                        if tc.get("function", {}).get("name"):
                            tool_calls[index]["function"]["name"] = tc["function"]["name"]
                        if tc.get("function", {}).get("arguments"):
                            tool_calls[index]["function"]["arguments"] += tc["function"][
                                "arguments"
                            ]

        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": full_content if full_content else None,
                        "tool_calls": tool_calls if tool_calls else None,
                    }
                }
            ]
        }

    @staticmethod
    def _is_transient_error(error_msg: str) -> bool:
        """Check if an error is transient (retryable) vs permanent."""
        error_lower = error_msg.lower()
        transient_keywords = {
            "timeout",
            "timed out",
            "connection",
            "reset",
            "refused",
            "temporarily unavailable",
            "too many requests",
            "rate limit",
            "502",
            "503",
            "504",
            "connection error",
        }
        return any(kw in error_lower for kw in transient_keywords)

    def _execute_tool_call(self, tool_call: dict) -> str:
        """Execute a single tool call and return the result.

        Automatically retries transient errors (timeout, network) but not permanent ones.
        """
        function = tool_call.get("function", {})
        name = function.get("name", "")
        arguments_str = function.get("arguments", "{}")

        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON arguments: {arguments_str}"

        # Permission check
        entry = registry._tools.get(name)
        is_read_only = entry.is_read_only if entry else False

        # Extract file_path and command for permission evaluation
        file_path = arguments.get("path")
        command = arguments.get("command")

        perm_result = self.permission_checker.evaluate(
            name,
            is_read_only=is_read_only,
            file_path=file_path,
            command=command,
        )

        if not perm_result.allowed:
            logger.warning("Tool call denied: %s — %s", name, perm_result.reason)
            return f"Error: {perm_result.reason}"

        if perm_result.requires_confirmation:
            # In auto mode this won't fire, but in ask mode we log it
            logger.info("Tool '%s' requires confirmation (mode=ask, auto-approved for CLI)", name)

        # Fire pre_tool_call hook (also fired in registry.dispatch, but we fire here
        # first so the permission check happens before the hook)
        hooks.emit(EVENT_PRE_TOOL_CALL, tool_name=name, args=arguments)

        # Execute with automatic retry on transient errors
        max_retries = max(0, self.config.get("agent", {}).get("tool_retry_max_attempts", 2))
        for attempt in range(max_retries + 1):
            # Pass config, memory, and agent reference to tool handlers via kwargs
            result = registry.dispatch(
                name,
                arguments,
                config=self.config,
                memory=self.memory,
                session_store=self.session_store,
                agent=self,
            )

            # Fire post_tool_call hook
            hooks.emit(EVENT_POST_TOOL_CALL, tool_name=name, args=arguments, result=result)

            # Retry on transient errors (timeout, network, rate-limit)
            is_transient = (
                isinstance(result, str)
                and result.startswith("Error:")
                and self._is_transient_error(result)
                and attempt < max_retries
            )
            if is_transient:
                wait_time = 2**attempt  # exponential backoff: 1s, 2s, 4s
                logger.warning(
                    "Tool %s failed with transient error (attempt %d/%d), retrying in %ds: %s",
                    name,
                    attempt + 1,
                    max_retries + 1,
                    wait_time,
                    result[:100],
                )
                time.sleep(wait_time)
                continue

            # Success or permanent error — return
            return result

        return result

    def _execute_tool_calls_parallel(
        self,
        tool_calls: list[dict],
    ) -> list[str]:
        """Execute tool calls, parallelizing independent ones.

        Tool calls are considered independent if they don't share data
        dependencies (i.e., none reads a file another writes). For safety,
        we parallelize only read-only tool calls; write/mutate tools run
        sequentially after the parallel batch.
        """
        from nova.tools.registry import _READ_ONLY_TOOLS

        read_only_calls = []
        write_calls = []

        for tc in tool_calls:
            fn_name = tc.get("function", {}).get("name", "")
            if fn_name in _READ_ONLY_TOOLS:
                read_only_calls.append(tc)
            else:
                write_calls.append(tc)

        results: list[str | None] = [None] * len(tool_calls)

        # Execute read-only tools in parallel
        if read_only_calls:
            max_workers = min(len(read_only_calls), 4)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_idx = {}
                for tc in read_only_calls:
                    idx = tool_calls.index(tc)
                    future = executor.submit(self._execute_tool_call, tc)
                    future_to_idx[future] = idx

                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        results[idx] = future.result()
                    except Exception as e:
                        fn_name = tool_calls[idx].get("function", {}).get("name", "")
                        logger.error("Parallel tool call '%s' failed: %s", fn_name, e)
                        results[idx] = f"Error: Tool '{fn_name}' failed: {e}"

                    # Report tool name to UI callback
                    tool_cb = getattr(self, "_tool_callback", None)
                    if tool_cb:
                        fn_name = tool_calls[idx].get("function", {}).get("name", "")
                        if fn_name:
                            tool_cb(fn_name)

        # Execute write/mutate tools sequentially
        for tc in write_calls:
            idx = tool_calls.index(tc)
            tool_cb = getattr(self, "_tool_callback", None)
            if tool_cb:
                fn_name = tc.get("function", {}).get("name", "")
                if fn_name:
                    tool_cb(fn_name)
            results[idx] = self._execute_tool_call(tc)

        return [r if r is not None else "Error: Unexpected None result" for r in results]

    def _estimate_messages_tokens_cached(self, messages: list[dict[str, Any]]) -> int:
        """Estimate message list tokens using a per-agent content cache.

        Messages that haven't changed since the last call are not re-encoded.
        Cache is bounded to 2048 entries to prevent unbounded growth.
        """
        import json

        from nova.tokens import estimate_tokens

        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                key = hash(content)
            else:
                key = hash(json.dumps(content, ensure_ascii=False, sort_keys=True))

            if key not in self._token_cache:
                if len(self._token_cache) >= 2048:
                    # Evict a random entry to stay bounded
                    self._token_cache.pop(next(iter(self._token_cache)))
                if isinstance(content, str):
                    self._token_cache[key] = estimate_tokens(content)
                elif isinstance(content, list):
                    subtotal = 0
                    for part in content:
                        if isinstance(part, dict):
                            subtotal += estimate_tokens(part.get("text", "") or "")
                        elif isinstance(part, str):
                            subtotal += estimate_tokens(part)
                    self._token_cache[key] = subtotal
                else:
                    self._token_cache[key] = 0
            total += self._token_cache[key] + 4  # +4 for message framing

        return total

    @staticmethod
    def _truncate_to_token_budget(text: str, max_tokens: int) -> str:
        """Truncate text to fit within a token budget.

        Uses head/tail truncation (70/20 ratio) to preserve beginning
        and end of the content.
        """
        from nova.tokens import estimate_tokens

        total_tokens = estimate_tokens(text)
        if total_tokens <= max_tokens:
            return text

        # Estimate chars per token ratio
        chars_per_token = len(text) / total_tokens if total_tokens > 0 else 4
        max_chars = int(max_tokens * chars_per_token)

        head_chars = int(max_chars * 0.70)
        tail_chars = int(max_chars * 0.20)

        if head_chars + tail_chars >= len(text):
            return text

        head = text[:head_chars]
        tail = text[-tail_chars:]
        truncated_tokens = (
            total_tokens
            - int(max_chars * 0.70 / chars_per_token)
            - int(tail_chars / chars_per_token)
        )

        return f"{head}\n\n[...{truncated_tokens:,} tokens truncated...]\n\n{tail}"

    def run(
        self,
        user_message: str,
        stream: bool = True,
        stream_callback: Callable[[str], None] | None = None,
    ) -> str:
        """Run a complete conversation turn.

        Returns the final assistant response.
        """
        # Add user message
        self.messages.append({"role": "user", "content": user_message})
        self.session_store.add_message(self.session_id or "", "user", user_message)

        # Build messages for API
        api_messages = [{"role": "system", "content": self._cached_system_prompt or ""}]
        api_messages.extend(self.messages)

        # Proactive history trimming: keep recent turns within budget
        turn_limit = self.config["budgets"].get("conversation_turn_limit", 15)
        max_messages = turn_limit * 4  # ~4 msgs per turn (user + assistant + tool pairs)
        if len(self.messages) > max_messages:
            # Keep the most recent messages, drop the oldest
            trim_count = len(self.messages) - max_messages
            logger.info(
                "Trimming %d oldest messages from conversation history "
                "(keeping last %d messages / ~%d turns)",
                trim_count,
                max_messages,
                turn_limit,
            )
            self.messages = self.messages[-max_messages:]
            api_messages = [{"role": "system", "content": self._cached_system_prompt or ""}]
            api_messages.extend(self.messages)

        # Get tool definitions
        tools = registry.get_definitions()

        # Main tool-calling loop
        max_iterations = self.config["agent"]["max_iterations"]
        iteration = 0
        # Optional interrupt hook — set by TUI via tui._interrupt_requested
        _interrupt_check: Callable[[], bool] | None = getattr(
            self,
            "_interrupt_check",
            None,
        )

        while iteration < max_iterations:
            iteration += 1

            # Check context window — apply microcompact if approaching budget
            total_tokens = (
                self._estimate_messages_tokens_cached(api_messages)
                + estimate_tokens(self._cached_system_prompt or "")
                + (estimate_tool_tokens(tools) if tools else 0)
            )
            compression_cfg = self.config.get("compression", {})
            microcompact_cfg = self.config.get("microcompact", {})
            if compression_cfg.get("enabled"):
                # Use model-specific context window
                context_window = get_model_context_window(
                    self.config["openrouter"]["model"],
                )
                threshold = int(context_window * compression_cfg.get("threshold_percent", 0.40))

                # Tier 1: Microcompact — strip old tool content (cheap, no LLM call)
                if microcompact_cfg.get("enabled", True) and total_tokens >= threshold:
                    keep_recent = microcompact_cfg.get("keep_recent", 6)
                    compacted = microcompact_messages(api_messages, keep_recent=keep_recent)
                    compacted_tokens = estimate_messages_tokens(compacted)
                    savings = total_tokens - compacted_tokens
                    if savings > 0:
                        logger.info(
                            "Microcompact saved %d tokens (%d → %d)",
                            savings,
                            total_tokens,
                            compacted_tokens,
                        )
                        api_messages = compacted
                        total_tokens = compacted_tokens

                # Tier 2: LLM-based context compression
                if total_tokens >= threshold:
                    summary_model = compression_cfg.get(
                        "summary_model",
                        self.config["openrouter"]["model"],
                    )
                    preserve_recent = microcompact_cfg.get("keep_recent", 6)
                    tokens_before_t2 = total_tokens
                    compressed = compress_conversation(
                        messages=api_messages,
                        http_client=self.client,
                        model=summary_model,
                        base_url=self.config["openrouter"]["base_url"],
                        api_key=self.config["openrouter"]["api_key"],
                        preserve_recent=preserve_recent,
                    )
                    if compressed:
                        api_messages = compressed
                        total_tokens = estimate_total_request_tokens(
                            api_messages,
                            system_prompt=self._cached_system_prompt or "",
                            tools=tools,
                        )
                        t2_savings = tokens_before_t2 - total_tokens
                        logger.info(
                            "LLM compression: %d → %d tokens (saved %d, %.0f%%)",
                            tokens_before_t2,
                            total_tokens,
                            t2_savings,
                            100 * t2_savings / tokens_before_t2 if tokens_before_t2 else 0,
                        )
                    else:
                        logger.warning(
                            "Context approaching compression threshold: %d >= %d tokens "
                            "(model: %s, window: %d). "
                            "Consider starting a new session.",
                            total_tokens,
                            threshold,
                            self.config["openrouter"]["model"],
                            context_window,
                        )

            # Call LLM
            response = self._call_llm(
                api_messages,
                tools=tools,
                stream=stream,
                stream_callback=stream_callback,
            )

            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content")
            tool_calls = message.get("tool_calls")

            # Add assistant message to history
            assistant_msg = {"role": "assistant"}
            if content:
                assistant_msg["content"] = content
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls

            self.messages.append(assistant_msg)
            self.session_store.add_message(
                self.session_id or "",
                "assistant",
                content or "",
                tool_calls=tool_calls,
            )
            api_messages.append(assistant_msg)

            # If no tool calls, we're done
            if not tool_calls:
                return content or ""

            # Check for interrupt between iterations (Ctrl+C)
            if _interrupt_check is not None and _interrupt_check():
                logger.info("Agent interrupted by user")
                return "[Interrupted]"

            # Execute tool calls — parallelize independent calls
            tool_result_max_tokens = self.config["budgets"].get("tool_result_max_tokens", 3000)
            results = self._execute_tool_calls_parallel(tool_calls)

            for tool_call, result in zip(tool_calls, results, strict=True):
                call_id = tool_call.get("id", "")

                # Enforce per-result token budget
                result_tokens = estimate_tokens(result)
                if result_tokens > tool_result_max_tokens:
                    result = self._truncate_to_token_budget(result, tool_result_max_tokens)

                tool_result_msg = {
                    "role": "tool",
                    "content": result,
                    "tool_call_id": call_id,
                }
                self.messages.append(tool_result_msg)
                self.session_store.add_message(
                    self.session_id or "",
                    "tool",
                    result,
                )
                api_messages.append(tool_result_msg)

        return f"[Max iterations ({max_iterations}) reached]"

    def chat_loop(self):
        """Run an interactive chat loop with prompt_toolkit TUI."""
        from rich.console import Console

        from nova.command_handlers import dispatch_command
        from nova.commands import resolve_command
        from nova.display import (
            NovaTUI,
            StreamingReasoningBox,
            print_banner,
            print_tool_calls,
        )

        console = Console()
        print_banner(console, self.config)

        model = self.config["openrouter"]["model"]
        context_window = get_model_context_window(model)
        tui = NovaTUI(model=model, context_window=context_window, config=self.config)
        self._reasoning_callback = None

        def on_input(user_input: str) -> None:
            from nova.display import _DIM, _RST, _cprint

            # Slash command dispatch via handler registry
            if user_input.startswith("/"):
                parts = user_input[1:].split(None, 1)
                cmd_name = parts[0].lower()
                cmd_args = parts[1] if len(parts) > 1 else ""
                cmd_def = resolve_command(cmd_name)

                if cmd_def is None:
                    return

                # Try the handler registry first; fall back to sending as message
                if dispatch_command(cmd_name, self, cmd_args):
                    return

                # Unknown/unhandled slash command — send as message to agent
                _cprint(f"{_DIM}(sending /{cmd_name} to agent){_RST}")

            # Regular message → agent
            display = StreamingReasoningBox()
            display.reset()
            tool_names: list[str] = []

            def stream_callback(chunk: str, d: StreamingReasoningBox = display) -> None:
                d.feed(chunk)

            def reasoning_callback(chunk: str, d: StreamingReasoningBox = display) -> None:
                d.feed_reasoning(chunk)

            # Print tool calls immediately as they execute (before response)
            _tl = tool_names

            def tool_callback(
                name: str, tl: list[str] = _tl, d: StreamingReasoningBox = display
            ) -> None:
                tl.append(name)
                # Flush any pending response content first, then show tool block
                d.flush()
                d.reset()
                print_tool_calls(tl[:])
                tl.clear()

            self._reasoning_callback = reasoning_callback
            self._tool_callback = tool_callback
            # Wire Ctrl+C interrupt into the agent loop
            self._interrupt_check = tui._interrupt_requested.is_set
            self.run(user_input, stream=True, stream_callback=stream_callback)
            self._interrupt_check = None
            display.flush()

            ctx = estimate_total_request_tokens(
                self.messages,
                system_prompt=self._cached_system_prompt or "",
            )
            tui.update_context(ctx)

        tui.run(on_input)
        self.close()
