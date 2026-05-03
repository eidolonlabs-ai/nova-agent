"""Hook/callback system for agent lifecycle events.

Lightweight Python callback registry that enables:
- Audit logging without modifying core code
- Custom tool result transformation
- Pre/post processing of LLM calls
- Session lifecycle hooks

Design: simple event-name → list of callbacks mapping.
Callbacks are synchronous functions that receive event-specific kwargs.
"""

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


# Supported event names
EVENT_PRE_TOOL_CALL = "pre_tool_call"
EVENT_POST_TOOL_CALL = "post_tool_call"
EVENT_PRE_LLM_CALL = "pre_llm_call"
EVENT_POST_LLM_CALL = "post_llm_call"
EVENT_SESSION_START = "session_start"
EVENT_SESSION_END = "session_end"

ALL_EVENTS: frozenset[str] = frozenset({
    EVENT_PRE_TOOL_CALL,
    EVENT_POST_TOOL_CALL,
    EVENT_PRE_LLM_CALL,
    EVENT_POST_LLM_CALL,
    EVENT_SESSION_START,
    EVENT_SESSION_END,
})


class HookRegistry:
    """Registry for lifecycle event callbacks.

    Usage:
        hooks = HookRegistry()
        hooks.on("pre_tool_call", lambda tool_name, args: log_audit(tool_name))
        hooks.on("post_tool_call", lambda tool_name, result: record_metric(result))
        hooks.emit("pre_tool_call", tool_name="terminal", args={"command": "ls"})
    """

    def __init__(self) -> None:
        self._callbacks: dict[str, list[Callable]] = defaultdict(list)

    def on(self, event: str, callback: Callable) -> None:
        """Register a callback for an event.

        Args:
            event: Event name (e.g. "pre_tool_call").
            callback: Callable that accepts **kwargs for the event.
        """
        if event not in ALL_EVENTS:
            logger.warning("Unknown hook event: %s", event)
        self._callbacks[event].append(callback)
        logger.debug("Registered hook for event: %s", event)

    def off(self, event: str, callback: Callable) -> bool:
        """Remove a callback for an event.

        Returns True if the callback was found and removed.
        """
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
            return True
        return False

    def emit(self, event: str, **kwargs: Any) -> list[Any]:
        """Emit an event, calling all registered callbacks.

        Args:
            event: Event name.
            **kwargs: Arguments passed to each callback.

        Returns:
            List of return values from callbacks.
        """
        results = []
        for callback in self._callbacks.get(event, []):
            try:
                result = callback(**kwargs)
                results.append(result)
            except Exception as e:
                logger.error("Hook error on event '%s': %s", event, e)
        return results

    def has_listeners(self, event: str) -> bool:
        """Check if any callbacks are registered for an event."""
        return bool(self._callbacks.get(event))

    def clear(self, event: str | None = None) -> None:
        """Clear callbacks. If event is None, clear all."""
        if event is None:
            self._callbacks.clear()
        else:
            self._callbacks.pop(event, None)


# Global hook registry
hooks = HookRegistry()
