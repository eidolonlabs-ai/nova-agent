"""Search sessions tool — find past conversations by keyword.

Allows the agent to search across all session titles and message content
using full-text search (FTS5) to find relevant past conversations.
"""

import logging
from typing import Any

from nova.tools.registry import registry

logger = logging.getLogger(__name__)

SEARCH_SESSIONS_SCHEMA = {
    "name": "search_sessions",
    "description": (
        "Search across all chat sessions by keyword. "
        "Returns matching sessions with their IDs, titles, and metadata. "
        "Use this to find past conversations before resuming or referencing them."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search keyword or phrase to find in session titles and messages.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 10).",
                "default": 10,
            },
        },
        "required": ["query"],
    },
}


def _search_sessions_tool(args: dict[str, Any], **kwargs) -> str:
    """Handle search_sessions tool calls."""
    session_store = kwargs.get("session_store")
    if session_store is None:
        return "Error: Session store is not available."

    query = args.get("query", "").strip()
    if not query:
        return "Error: 'query' is required."

    limit = args.get("limit", 10)
    try:
        limit = min(max(int(limit), 1), 50)  # Clamp to 1-50
    except (ValueError, TypeError):
        limit = 10

    results = session_store.search_sessions(query, limit=limit)
    if not results:
        return f"No sessions found matching '{query}'."

    lines = [f"Found {len(results)} session(s) matching '{query}':"]
    for i, session in enumerate(results, 1):
        session_id = session.get("session_id", "unknown")
        title = session.get("title") or "(untitled)"
        updated = session.get("updated_at", "")[:19]
        msg_count = session.get("message_count", 0)
        lines.append(f"{i}. [{session_id}] {title}")
        lines.append(f"   Updated: {updated} | Messages: {msg_count}")

    return "\n".join(lines)


registry.register(
    name="search_sessions",
    toolset="sessions",
    schema=SEARCH_SESSIONS_SCHEMA,
    handler=_search_sessions_tool,
    emoji="🔍",
    is_read_only=True,
)
