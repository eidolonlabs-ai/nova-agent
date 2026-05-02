"""Main agent loop.

Handles the conversation loop with tool calling, streaming,
context compression, and session management.
"""

import json
import logging
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

        # Discover tools
        discover_builtin_tools()

        # Create or load session
        if self.session_id:
            self._load_session()
        else:
            self._create_session()

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

    def _build_system_prompt(self, mode: str = "full"):
        """Build the system prompt with budget enforcement."""
        memory_content = None
        if self.memory:
            memory_content = self.memory.format_for_prompt()

        self._system_prompt = build_system_prompt(
            config=self.config,
            mode=mode,
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
            return self._stream_response(payload, stream_callback)

        response = self.client.post("/chat/completions", json=payload)
        if response.status_code == 400:
            logger.error("API 400 error. Payload: %s", json.dumps(payload, indent=2)[:2000])
            logger.error("Response: %s", response.text[:1000])
        response.raise_for_status()
        return response.json()

    def _stream_response(
        self,
        payload: dict,
        callback: Callable[[str], None] | None = None,
    ) -> dict:
        """Stream a response from the API."""
        payload["stream"] = True

        full_content = ""
        tool_calls: list[dict[str, Any]] = []

        with self.client.stream("POST", "/chat/completions", json=payload) as response:
            if response.status_code == 400:
                body = response.read().decode()
                logger.error("API 400 error. Payload: %s", json.dumps(payload, indent=2)[:2000])
                logger.error("Response: %s", body[:1000])
                raise httpx.HTTPStatusError(
                    f"Bad Request: {body[:500]}",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                delta = data.get("choices", [{}])[0].get("delta", {})

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

            # Execute tool calls
            tool_result_max = self.config["budgets"].get("tool_result_max_chars", 8000)
            for tool_call in tool_calls:
                call_id = tool_call.get("id", "")
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
        """Run an interactive chat loop."""
        from rich.console import Console
        from rich.prompt import Prompt

        console = Console()
        console.print(
            "[bold green]Nova Agent[/bold green] — "
            "Type 'quit' to exit, 'new' for new session"
        )
        console.print()

        while True:
            try:
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Goodbye![/dim]")
                break

            if user_input.lower() in ("quit", "exit", "q"):
                console.print("[dim]Goodbye![/dim]")
                break

            if user_input.lower() == "new":
                self._create_session()
                console.print("[dim]New session started[/dim]")
                continue

            if not user_input.strip():
                continue

            console.print()
            console.print("[bold yellow]Nova[/bold yellow]: ", end="")

            # Collect streamed content
            full_response = ""

            def stream_callback(chunk: str):
                nonlocal full_response
                full_response += chunk
                console.print(chunk, end="")

            console.print()

            self.run(user_input, stream=True, stream_callback=stream_callback)
            console.print()
