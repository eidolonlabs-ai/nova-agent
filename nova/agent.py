"""Main agent loop.

Handles the conversation loop with tool calling, streaming,
context compression, and session management.
"""

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from nova.config import ensure_nova_home, load_config
from nova.memory import MemoryStore
from nova.model_metadata import get_model_context_window
from nova.prompt import build_system_prompt
from nova.session import SessionStore
from nova.tokens import estimate_total_request_tokens
from nova.tools.registry import discover_builtin_tools, registry

logger = logging.getLogger(__name__)


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

        # Sub-agent depth tracking
        self.depth: int = self.config.get("_subagent_depth", 0)
        max_spawn_depth = self.config.get("delegation", {}).get("max_spawn_depth", 2)
        self.is_leaf_agent: bool = self.depth >= max_spawn_depth

        # Discover tools (pass config so delegation tool can be gated)
        discover_builtin_tools(self.config)

        # Create or load session
        if self.session_id:
            self._load_session()
        else:
            self._create_session()

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
                self.session_id, limit=turn_limit * 4,  # ~4 msgs per turn (user+assistant+tool pairs)
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
                self.session_id, self._system_prompt or "",
            )

    def _call_llm(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        stream: bool = False,
        stream_callback: Callable[[str], None] | None = None,
    ) -> dict:
        """Make an API call to OpenRouter."""
        openrouter_config = self.config["openrouter"]
        agent_config = self.config["agent"]

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

        if stream:
            return self._stream_response(payload, stream_callback, getattr(self, "_reasoning_callback", None))

        response = self.client.post("/chat/completions", json=payload)
        if response.status_code == 400:
            # Sanitize payload before logging — never log API keys or full messages
            safe_payload = {
                "model": payload.get("model"),
                "message_count": len(payload.get("messages", [])),
                "has_tools": "tools" in payload,
            }
            logger.error("API 400 error. Request: %s", json.dumps(safe_payload))
            logger.error("Response: %s", response.text[:1000])
        response.raise_for_status()
        return response.json()

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
                # Sanitize payload before logging
                safe_payload = {
                    "model": payload.get("model"),
                    "message_count": len(payload.get("messages", [])),
                    "has_tools": "tools" in payload,
                }
                logger.error("API 400 error. Request: %s", json.dumps(safe_payload))
                logger.error("Response: %s", body[:1000])
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
                    logger.warning("Stream watchdog: no data for %.0fs, aborting", _watchdog_timeout)
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
                            tool_calls.append({
                                "id": tc.get("id", ""),
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            })
                        if tc.get("function", {}).get("name"):
                            tool_calls[index]["function"]["name"] = tc["function"]["name"]
                        if tc.get("function", {}).get("arguments"):
                            tool_calls[index]["function"]["arguments"] += tc[
                                "function"
                            ]["arguments"]

        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": full_content if full_content else None,
                    "tool_calls": tool_calls if tool_calls else None,
                }
            }]
        }

    def _execute_tool_call(self, tool_call: dict) -> str:
        """Execute a single tool call and return the result."""
        function = tool_call.get("function", {})
        name = function.get("name", "")
        arguments_str = function.get("arguments", "{}")

        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON arguments: {arguments_str}"

        # Pass config, memory, and agent reference to tool handlers via kwargs
        return registry.dispatch(
            name, arguments, config=self.config, memory=self.memory, agent=self,
        )

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
                trim_count, max_messages, turn_limit,
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
        _interrupt_check = getattr(self, "_interrupt_check", None)

        while iteration < max_iterations:
            iteration += 1

            # Check context window — warn when approaching budget
            total_tokens = estimate_total_request_tokens(
                api_messages,
                system_prompt=self._cached_system_prompt or "",
                tools=tools,
            )
            compression_cfg = self.config.get("compression", {})
            if compression_cfg.get("enabled"):
                # Use model-specific context window
                context_window = get_model_context_window(
                    self.config["openrouter"]["model"],
                )
                threshold = int(context_window * compression_cfg.get("threshold_percent", 0.40))
                if total_tokens >= threshold:
                    logger.warning(
                        "Context approaching compression threshold: %d >= %d tokens "
                        "(model: %s, window: %d). "
                        "Compression not yet implemented — consider starting a new session.",
                        total_tokens, threshold,
                        self.config["openrouter"]["model"], context_window,
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

            # Execute tool calls
            tool_result_max = self.config["budgets"].get("tool_result_max_chars", 8000)
            for tool_call in tool_calls:
                call_id = tool_call.get("id", "")
                # Report tool name to UI callback if registered
                tool_cb = getattr(self, "_tool_callback", None)
                if tool_cb:
                    fn_name = tool_call.get("function", {}).get("name", "")
                    if fn_name:
                        tool_cb(fn_name)
                result = self._execute_tool_call(tool_call)

                # Enforce per-result token budget
                if len(result) > tool_result_max:
                    head = int(tool_result_max * 0.7)
                    tail = int(tool_result_max * 0.2)
                    result = (
                        f"{result[:head]}\n\n"
                        f"[...{len(result) - head - tail:,} chars truncated...]\n\n"
                        f"{result[-tail:]}"
                    )

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
        tui = NovaTUI(model=model, context_window=context_window)
        self._reasoning_callback = None

        def on_input(user_input: str) -> None:
            from nova.commands import resolve_command
            from nova.display import _CYAN, _DIM, _RST, _cprint

            # Slash command dispatch
            if user_input.startswith("/"):
                parts = user_input[1:].split(None, 1)
                cmd_name = parts[0].lower()
                cmd_args = parts[1] if len(parts) > 1 else ""
                cmd_def = resolve_command(cmd_name)

                if cmd_def is None:
                    return

                name = cmd_def.name

                if name == "new":
                    self._create_session()
                    _cprint(f"{_DIM}New session started{_RST}")
                    return

                if name == "history":
                    for msg in self.messages:
                        role = msg.get("role", "")
                        content = msg.get("content") or ""
                        if role == "user":
                            _cprint(f"\n{_CYAN}❯ {content}{_RST}")
                        elif role == "assistant" and content:
                            preview = content[:200] + "…" if len(content) > 200 else content
                            _cprint(f"  {preview}")
                    return

                if name == "status":
                    ctx = estimate_total_request_tokens(
                        self.messages,
                        system_prompt=self._cached_system_prompt or "",
                    )
                    _cprint(f"{_DIM}Session: {self.session_id}")
                    _cprint(f"Model:   {self.config['openrouter']['model']}")
                    _cprint(f"Context: {ctx:,} tokens")
                    # Delegation state
                    delegation_cfg = self.config.get("delegation", {})
                    if delegation_cfg.get("enabled"):
                        max_depth = delegation_cfg.get("max_spawn_depth", 2)
                        role = "leaf" if self.is_leaf_agent else "orchestrator"
                        _cprint(f"Delegation: enabled  depth={self.depth}/{max_depth}  role={role}")
                    else:
                        _cprint("Delegation: disabled")
                    _cprint(f"Messages: {len(self.messages)}{_RST}")
                    return

                if name == "sessions":
                    sessions = self.session_store.list_sessions(limit=10)
                    if not sessions:
                        _cprint(f"{_DIM}No sessions found{_RST}")
                    for s in sessions:
                        _cprint(f"{_DIM}{s.get('id', '')}  {s.get('created_at', '')}{_RST}")
                    return

                if name == "model":
                    if cmd_args:
                        self.config["openrouter"]["model"] = cmd_args.strip()
                        tui.model_short = cmd_args.strip().split("/")[-1]
                        _cprint(f"{_DIM}Model switched to: {cmd_args.strip()}{_RST}")
                    else:
                        _cprint(f"{_DIM}Current model: {self.config['openrouter']['model']}{_RST}")
                    return

                if name == "tools":
                    from nova.tools.registry import registry
                    tools = registry.get_definitions()
                    _cprint(f"{_DIM}Available tools ({len(tools)}):{_RST}")
                    for t in tools:
                        _cprint(f"  {_CYAN}{t['function']['name']}{_RST}{_DIM}  —  {t['function'].get('description', '')[:60]}{_RST}")
                    return

                if name == "usage":
                    ctx = estimate_total_request_tokens(
                        self.messages,
                        system_prompt=self._cached_system_prompt or "",
                    )
                    cw = get_model_context_window(self.config["openrouter"]["model"])
                    pct = int(ctx / cw * 100) if cw else 0
                    _cprint(f"{_DIM}Context used: {ctx:,} / {cw:,} tokens ({pct}%){_RST}")
                    return

                if name == "undo":
                    # Remove last user+assistant pair
                    if len(self.messages) >= 2:
                        self.messages = self.messages[:-2]
                        _cprint(f"{_DIM}Last exchange removed{_RST}")
                    else:
                        _cprint(f"{_DIM}Nothing to undo{_RST}")
                    return

                if name == "compact":
                    _cprint(f"{_DIM}Compacting context…{_RST}")
                    # Keep system prompt + last 4 messages
                    if len(self.messages) > 4:
                        self.messages = self.messages[-4:]
                    _cprint(f"{_DIM}Context compacted to {len(self.messages)} messages{_RST}")
                    return

                if name == "copy":
                    # Find last assistant message
                    for msg in reversed(self.messages):
                        if msg.get("role") == "assistant" and msg.get("content"):
                            import subprocess
                            subprocess.run(
                                ["pbcopy"],
                                input=msg["content"].encode(),
                                check=False,
                            )
                            _cprint(f"{_DIM}Copied to clipboard{_RST}")
                            return
                    _cprint(f"{_DIM}No response to copy{_RST}")
                    return

                if name == "memory":
                    sub = cmd_args.split(None, 1)[0].lower() if cmd_args else "list"
                    query = cmd_args.split(None, 1)[1] if len(cmd_args.split(None, 1)) > 1 else ""
                    if not self.memory:
                        _cprint(f"{_DIM}Memory is disabled{_RST}")
                        return
                    if sub == "clear":
                        self.memory.clear()
                        _cprint(f"{_DIM}Memory cleared{_RST}")
                    elif sub == "search" and query:
                        results = self.memory.search(query)
                        for r in results:
                            _cprint(f"  {_DIM}{r}{_RST}")
                    else:
                        entries = self.memory.get_all()
                        if not entries:
                            _cprint(f"{_DIM}No memories stored{_RST}")
                        for e in entries:
                            _cprint(f"  {_DIM}{e}{_RST}")
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
            def tool_callback(name: str, tl: list[str] = _tl, d: StreamingReasoningBox = display) -> None:
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
