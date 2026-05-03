"""Central tool registry.

Each tool file calls registry.register() at module level to declare its
schema, handler, and metadata. The agent queries the registry for tool
definitions and dispatches tool calls.
"""

import logging
from collections.abc import Callable
from typing import Any

from nova.hooks import EVENT_POST_TOOL_CALL, EVENT_PRE_TOOL_CALL

logger = logging.getLogger(__name__)


# Tools that are inherently read-only (never mutate state)
_READ_ONLY_TOOLS: frozenset[str] = frozenset({
    "read_file",
    "search_files",
    "web_search",
    "skills_list",
    "skill_view",
})


class ToolEntry:
    """Metadata for a single registered tool."""

    __slots__ = (
        "name", "toolset", "schema", "handler", "check_fn",
        "description", "emoji", "is_read_only",
    )

    def __init__(
        self,
        name: str,
        toolset: str,
        schema: dict,
        handler: Callable,
        check_fn: Callable | None = None,
        description: str = "",
        emoji: str = "🔧",
        is_read_only: bool = False,
    ):
        self.name = name
        self.toolset = toolset
        self.schema = schema
        self.handler = handler
        self.check_fn = check_fn
        self.description = description
        self.emoji = emoji
        self.is_read_only = is_read_only


class ToolRegistry:
    """Singleton registry for tool schemas and handlers."""

    def __init__(self):
        self._tools: dict[str, ToolEntry] = {}
        self._generation: int = 0

    def register(
        self,
        name: str,
        toolset: str,
        schema: dict,
        handler: Callable,
        check_fn: Callable | None = None,
        emoji: str = "🔧",
        is_read_only: bool = False,
    ):
        """Register a tool."""
        # Auto-detect read-only status if not explicitly set
        if not is_read_only:
            is_read_only = name in _READ_ONLY_TOOLS
        self._tools[name] = ToolEntry(
            name=name,
            toolset=toolset,
            schema=schema,
            handler=handler,
            check_fn=check_fn,
            description=schema.get("description", ""),
            emoji=emoji,
            is_read_only=is_read_only,
        )
        self._generation += 1
        logger.debug("Registered tool: %s", name)

    def get_definitions(self, tool_names: set | None = None) -> list[dict]:
        """Get tool schema definitions for API calls.

        Returns tools in OpenAI-compatible format:
        {"type": "function", "function": {schema}}

        If tool_names is provided, only return those tools.
        Otherwise return all registered tools.
        """
        tools = []
        for name, entry in self._tools.items():
            if tool_names is None or name in tool_names:
                # Skip check_fn for now (simplified)
                tools.append({
                    "type": "function",
                    "function": entry.schema,
                })
        return tools

    def get_tool_summary_list(self, tool_names: set | None = None) -> str:
        """Get a compact bullet list of tool names + one-line descriptions.

        Used in the system prompt for efficient tokenization.
        """
        lines = []
        for name, entry in sorted(self._tools.items()):
            if tool_names is None or name in tool_names:
                desc = entry.description.split("\n")[0][:100]
                lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    def dispatch(self, name: str, args: dict, **kwargs) -> Any:
        """Dispatch a tool call by name.

        Fires pre_tool_call and post_tool_call hooks if registered.
        """
        entry = self._tools.get(name)
        if not entry:
            return f"Error: Unknown tool '{name}'"

        # Fire pre_tool_call hook
        from nova.hooks import hooks as _hooks
        _hooks.emit(EVENT_PRE_TOOL_CALL, tool_name=name, args=args)

        try:
            result = entry.handler(args, **kwargs)
            # Fire post_tool_call hook
            _hooks.emit(EVENT_POST_TOOL_CALL, tool_name=name, args=args, result=result)
            return result
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            error_result = f"Error: Tool '{name}' failed: {e}"
            _hooks.emit(EVENT_POST_TOOL_CALL, tool_name=name, args=args, result=error_result)
            return error_result

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def all_tool_names(self) -> set:
        return set(self._tools.keys())


# Global registry instance
registry = ToolRegistry()


def discover_builtin_tools(config: dict | None = None):
    """Import built-in tool modules to trigger registration.

    Args:
        config: Agent config dict, used to gate optional tools like delegate_task.
    """
    import importlib

    tool_modules = [
        "nova.tools.terminal",
        "nova.tools.file_ops",
        "nova.tools.search_files",
        "nova.tools.web",
        "nova.tools.skills_tool",
        "nova.tools.memory_tool",
        "nova.tools.task_tools",
    ]

    for mod_name in tool_modules:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            logger.warning("Could not import tool module %s: %s", mod_name, e)

    # Delegation tool is gated on config flag and agent depth
    try:
        from nova.tools.delegate_tool import register_delegate_tool
        depth = (config or {}).get("_subagent_depth", 0)
        max_depth = (config or {}).get("delegation", {}).get("max_spawn_depth", 2)
        if depth < max_depth:
            register_delegate_tool(config)
    except Exception as e:
        logger.warning("Could not register delegate_task tool: %s", e)
