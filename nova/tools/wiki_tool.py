"""Wiki tool — manage Obsidian-compatible wiki notes."""

import json
import logging
from typing import Any

from nova.tools.registry import registry

logger = logging.getLogger(__name__)

WIKI_TOOL_SCHEMA = {
    "name": "wiki",
    "description": (
        "Manage wiki knowledge notes in an Obsidian-compatible vault. "
        "Actions: write (create/update note), append (add to note), "
        "read (fetch note), search (full-text), list (all notes), delete (remove), "
        "maintenance (read-only report of duplicates, orphans, and stale notes). "
        "Titles support path prefixes for folders: 'People/Mark', 'Projects/nova'. "
        "Use [[wikilinks]] and #tags in content."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["write", "append", "read", "search", "list", "delete", "maintenance"],
                "description": "The wiki action to perform.",
            },
            "title": {
                "type": "string",
                "description": (
                    "Note title or path (e.g. 'People/Mark', 'Projects/nova'). "
                    "Required for write, append, read, delete."
                ),
            },
            "content": {
                "type": "string",
                "description": "Note content in markdown. Required for write and append.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for the note (write only).",
            },
            "query": {
                "type": "string",
                "description": "Full-text search query (search only).",
            },
            "tag": {
                "type": "string",
                "description": "Filter notes by tag (list only).",
            },
            "stale_days": {
                "type": "integer",
                "description": "Notes not modified within this many days are flagged stale (maintenance only). Default 90.",
            },
        },
        "required": ["action"],
    },
}


def _wiki_tool(args: dict[str, Any], **kwargs) -> str:
    wiki = kwargs.get("wiki")
    if wiki is None:
        return "Error: Wiki memory is not enabled."

    action = args.get("action", "")

    try:
        return _dispatch(wiki, action, args, kwargs)
    except ValueError as e:
        return f"Error: {e}"


def _dispatch(wiki, action: str, args: dict[str, Any], kwargs: dict) -> str:
    if action == "write":
        title = args.get("title", "").strip()
        content = args.get("content", "")
        if not title:
            return "Error: 'title' is required for write."
        if not content:
            return "Error: 'content' is required for write."
        tags = args.get("tags") or []
        result = wiki.write(title, content, tags)
        _refresh(kwargs)
        return json.dumps(result)

    elif action == "append":
        title = args.get("title", "").strip()
        content = args.get("content", "")
        if not title:
            return "Error: 'title' is required for append."
        if not content:
            return "Error: 'content' is required for append."
        result = wiki.append(title, content)
        _refresh(kwargs)
        return json.dumps(result)

    elif action == "read":
        title = args.get("title", "").strip()
        if not title:
            return "Error: 'title' is required for read."
        note = wiki.read(title)
        if note is None:
            return f"Note not found: '{title}'"
        fm = note["frontmatter"]
        header = f"# {fm.get('title', title)}"
        meta = []
        if fm.get("tags"):
            meta.append("tags: " + ", ".join(f"#{t}" for t in fm["tags"]))
        if fm.get("modified"):
            meta.append(f"modified: {fm['modified']}")
        meta_line = " | ".join(meta)
        parts = [header]
        if meta_line:
            parts.append(meta_line)
        parts.append("")
        parts.append(note["content"])
        return "\n".join(parts)

    elif action == "search":
        query = args.get("query", "").strip()
        if not query:
            return "Error: 'query' is required for search."
        results = wiki.search(query)
        if not results:
            return f"No notes found matching '{query}'."
        return json.dumps(results, indent=2, ensure_ascii=False)

    elif action == "list":
        tag = args.get("tag")
        notes = wiki.list_notes(tag=tag)
        if not notes:
            return "No notes found."
        return json.dumps(notes, indent=2, ensure_ascii=False)

    elif action == "delete":
        title = args.get("title", "").strip()
        if not title:
            return "Error: 'title' is required for delete."
        deleted = wiki.delete(title)
        _refresh(kwargs)
        return json.dumps({"status": "deleted" if deleted else "not_found"})

    elif action == "maintenance":
        stale_days = args.get("stale_days", 90)
        report = wiki.maintenance(stale_days=stale_days)
        return json.dumps(report, indent=2, ensure_ascii=False)

    return (
        f"Error: Unknown action '{action}'. "
        "Use write, append, read, search, list, delete, or maintenance."
    )


def _refresh(kwargs: dict) -> None:
    agent = kwargs.get("agent")
    if agent and hasattr(agent, "_refresh_system_prompt"):
        agent._refresh_system_prompt()


registry.register(
    name="wiki",
    toolset="wiki",
    schema=WIKI_TOOL_SCHEMA,
    handler=_wiki_tool,
    emoji="📓",
)
