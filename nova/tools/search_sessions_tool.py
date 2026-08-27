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
        "Read messages from a past chat session by ID. "
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
                "description": "Maximum number of most-recent messages to return (default: 100).",
            },
            "around_idx": {
                "type": "integer",
                "description": "Optional message index to center a small context window around.",
            },
            "radius": {
                "type": "integer",
                "description": "Messages on each side of around_idx (default: 2, maximum: 20).",
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

    raw_limit = args.get("limit", 100)
    try:
        limit = min(max(int(raw_limit), 1), 200)  # Clamp to 1-200
    except (ValueError, TypeError):
        limit = 100

    around_idx = args.get("around_idx")
    try:
        around_idx = int(around_idx) if around_idx is not None else None
    except (ValueError, TypeError):
        return "Error: 'around_idx' must be an integer."
    messages = session_store.get_messages(
        session_id,
        limit=limit if around_idx is None else None,
        around_idx=around_idx,
        radius=args.get("radius", 2),
    )
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

SEARCH_MESSAGES_SCHEMA = {
    "name": "search_messages",
    "description": (
        "Search individual messages across chat sessions. Returns bounded historical "
        "snippets and indexes; use read_session with around_idx for nearby context."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Keyword or phrase to search for."},
            "limit": {"type": "integer", "description": "Maximum results (default: 10)."},
            "session_id": {"type": "string", "description": "Optional session ID filter."},
        },
        "required": ["query"],
    },
}


def _search_messages_tool(args: dict[str, Any], **kwargs) -> str:
    session_store = kwargs.get("session_store")
    if session_store is None:
        return "Error: Session store is not available."
    query = args.get("query", "").strip()
    if not query:
        return "Error: 'query' is required."
    try:
        limit = min(max(int(args.get("limit", 10)), 1), 50)
    except (ValueError, TypeError):
        limit = 10
    results = session_store.search_messages(
        query, limit=limit, session_id=args.get("session_id") or None
    )
    if not results:
        return f"No messages found matching '{query}'."
    lines = [f"Found {len(results)} message(s) matching '{query}':"]
    for index, result in enumerate(results, 1):
        lines.append(
            f"{index}. [{result['session_id']}] {result['title'] or '(untitled)'} "
            f"message {result['idx']} ({result['role']})"
        )
        lines.append(f"   Historical data: {result['snippet']}")
    return "\n".join(lines)


registry.register(
    name="search_messages",
    toolset="sessions",
    schema=SEARCH_MESSAGES_SCHEMA,
    handler=_search_messages_tool,
    emoji="🔎",
    is_read_only=True,
)
