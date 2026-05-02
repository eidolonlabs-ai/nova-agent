"""Memory tool — manage persistent memories.

Provides memory add/search/delete/clear tools for the agent
to store and recall durable facts.
"""

import json
import logging
from typing import Any

from nova.tools.registry import registry

logger = logging.getLogger(__name__)

MEMORY_TOOL_SCHEMA = {
    "name": "memory",
    "description": (
        "Manage persistent memory. Actions: "
        "add (save a fact), search (find memories), "
        "delete (remove by id), clear (erase all). "
        "Save durable facts: user preferences, environment details, tool quirks. "
        "Do NOT save task progress or temporary state."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "search", "delete", "clear"],
                "description": "The memory action to perform.",
            },
            "content": {
                "type": "string",
                "description": "The memory content to save (for 'add' action).",
            },
            "category": {
                "type": "string",
                "description": "Category for the memory (for 'add' action, default: 'general').",
                "default": "general",
            },
            "query": {
                "type": "string",
                "description": "Search query (for 'search' action).",
            },
            "id": {
                "type": "string",
                "description": "Memory ID to delete (for 'delete' action).",
            },
        },
        "required": ["action"],
    },
}


def _memory_tool(args: dict[str, Any], **kwargs) -> str:
    """Handle memory tool calls."""
    memory_store = kwargs.get("memory")
    if memory_store is None:
        return "Error: Memory is not enabled."

    action = args.get("action", "")
    needs_refresh = False

    if action == "add":
        content = args.get("content", "")
        if not content:
            return "Error: 'content' is required for add action."
        category = args.get("category", "general")
        entry = memory_store.add(content=content, category=category)
        needs_refresh = True
        result = json.dumps({"status": "saved", "id": entry["id"]})

    elif action == "search":
        query = args.get("query", "")
        if not query:
            return "Error: 'query' is required for search action."
        results = memory_store.search(query)
        if not results:
            return f"No memories found for '{query}'."
        return json.dumps(results, indent=2)

    elif action == "delete":
        entry_id = args.get("id", "")
        if not entry_id:
            return "Error: 'id' is required for delete action."
        success = memory_store.delete(entry_id)
        needs_refresh = True
        result = json.dumps({"status": "deleted" if success else "not_found"})

    elif action == "clear":
        memory_store.clear()
        needs_refresh = True
        result = json.dumps({"status": "cleared"})

    else:
        return f"Error: Unknown action '{action}'. Use 'add', 'search', 'delete', or 'clear'."

    # Trigger system prompt refresh so new memory is visible next turn
    if needs_refresh:
        agent = kwargs.get("agent")
        if agent and hasattr(agent, "_refresh_system_prompt"):
            agent._refresh_system_prompt()

    return result


registry.register(
    name="memory",
    toolset="memory",
    schema=MEMORY_TOOL_SCHEMA,
    handler=_memory_tool,
    emoji="🧠",
)
