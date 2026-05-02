"""Central tool registry.

Each tool file calls registry.register() at module level to declare its
schema, handler, and metadata. The agent queries the registry for tool
definitions and dispatches tool calls.
"""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class ToolEntry:
    """Metadata for a single registered tool."""

    __slots__ = (
        "name", "toolset", "schema", "handler", "check_fn",
        "description", "emoji",
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
    ):
        self.name = name
        self.toolset = toolset
        self.schema = schema
        self.handler = handler
        self.check_fn = check_fn
        self.description = description
        self.emoji = emoji


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
    ):
        """Register a tool."""
        self._tools[name] = ToolEntry(
            name=name,
            toolset=toolset,
            schema=schema,
            handler=handler,
            check_fn=check_fn,
            description=schema.get("description", ""),
            emoji=emoji,
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
        """Dispatch a tool call by name."""
        entry = self._tools.get(name)
        if not entry:
            return f"Error: Unknown tool '{name}'"

        try:
            result = entry.handler(args, **kwargs)
            return result
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            return f"Error: Tool '{name}' failed: {e}"

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def all_tool_names(self) -> set:
        return set(self._tools.keys())


# Global registry instance
registry = ToolRegistry()


def discover_builtin_tools():
    """Import built-in tool modules to trigger registration."""
    import importlib

    tool_modules = [
        "nova.tools.terminal",
        "nova.tools.file_ops",
        "nova.tools.search_files",
        "nova.tools.web",
        "nova.tools.skills_tool",
        "nova.tools.memory_tool",
    ]

    for mod_name in tool_modules:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            logger.warning("Could not import tool module %s: %s", mod_name, e)
