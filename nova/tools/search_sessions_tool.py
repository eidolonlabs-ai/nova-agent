"""Session tools — search and read past conversations.

search_sessions: FTS5 keyword search across all session titles and messages.
read_session: fetch the full message history for a given session ID.
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

READ_SESSION_SCHEMA = {
    "name": "read_session",
    "description": (
        "Read the full message history of a past chat session by ID. "
        "Use search_sessions first to find the session ID, then call this "
        "to retrieve the actual conversation content."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "The session ID to read (from search_sessions results).",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of most-recent messages to return (default: all).",
            },
        },
        "required": ["session_id"],
    },
}


def _read_session_tool(args: dict[str, Any], **kwargs) -> str:
    session_store = kwargs.get("session_store")
    if session_store is None:
        return "Error: Session store is not available."

    session_id = args.get("session_id", "").strip()
    if not session_id:
        return "Error: 'session_id' is required."

    info = session_store.get_session_info(session_id)
    if info is None:
        return f"Error: Session '{session_id}' not found."

    limit = args.get("limit")
    try:
        limit = min(max(int(limit), 1), 200) if limit is not None else None  # Clamp to 1-200
    except (ValueError, TypeError):
        limit = None

    messages = session_store.get_messages(session_id, limit=limit)
    if not messages:
        return f"Session '{session_id}' has no messages."

    title = info.get("title") or "(untitled)"
    lines = [f"Session: {title} [{session_id}]", f"Messages: {len(messages)}", ""]
    for msg in messages:
        role = msg["role"].upper()
        content = msg["content"]
        lines.append(f"[{role}] {content}")
        lines.append("")

    return "\n".join(lines).rstrip()


registry.register(
    name="read_session",
    toolset="sessions",
    schema=READ_SESSION_SCHEMA,
    handler=_read_session_tool,
    emoji="📖",
    is_read_only=True,
)
