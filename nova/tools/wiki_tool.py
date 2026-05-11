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
        "rename (rename note + update all backlinks), "
        "list_tags (all tags with counts), rename_tag (rename tag globally), "
        "maintenance (read-only report: duplicates, broken links, orphans, stale), "
        "follow (BFS graph traversal via [[wikilinks]]), "
        "backlinks (find notes that link to a title). "
        "Titles support path prefixes: 'People/Mark', 'Projects/nova'. "
        "Use [[wikilinks]] and #tags in content. "
        "Set inject:true in frontmatter to pin a note into every system prompt."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "write",
                    "append",
                    "read",
                    "search",
                    "list",
                    "delete",
                    "rename",
                    "list_tags",
                    "rename_tag",
                    "maintenance",
                    "follow",
                    "backlinks",
                ],
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
            "depth": {
                "type": "integer",
                "description": "Max hops to follow from the start note (follow only). Default 2.",
            },
            "max_notes": {
                "type": "integer",
                "description": "Max notes to return (follow only). Default 10.",
            },
            "include_content": {
                "type": "boolean",
                "description": (
                    "Include full note content in each follow result node (follow only). "
                    "Default false. Use true to read a whole neighbourhood in one call "
                    "instead of following up with separate wiki read calls."
                ),
            },
            "new_title": {
                "type": "string",
                "description": "New note title (rename only).",
            },
            "old_tag": {
                "type": "string",
                "description": "Tag to rename from (rename_tag only).",
            },
            "new_tag": {
                "type": "string",
                "description": "Tag to rename to (rename_tag only).",
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
        broken = len(wiki.backlinks(title))
        deleted = wiki.delete(title)
        _refresh(kwargs)
        response: dict = {"status": "deleted" if deleted else "not_found"}
        if deleted and broken > 0:
            response["warning"] = (
                f"{broken} note(s) still link to '[[{title}]]' — consider updating them."
            )
        return json.dumps(response)

    elif action == "rename":
        title = args.get("title", "").strip()
        new_title = args.get("new_title", "").strip()
        if not title:
            return "Error: 'title' is required for rename."
        if not new_title:
            return "Error: 'new_title' is required for rename."
        result = wiki.rename(title, new_title)
        if result.get("status") == "renamed":
            _refresh(kwargs)
        return json.dumps(result)

    elif action == "list_tags":
        tags = wiki.list_tags()
        if not tags:
            return "No tags found."
        return json.dumps(tags, indent=2, ensure_ascii=False)

    elif action == "rename_tag":
        old_tag = args.get("old_tag", "").strip()
        new_tag = args.get("new_tag", "").strip()
        if not old_tag:
            return "Error: 'old_tag' is required for rename_tag."
        if not new_tag:
            return "Error: 'new_tag' is required for rename_tag."
        result = wiki.rename_tag(old_tag, new_tag)
        if result.get("updated_notes"):
            _refresh(kwargs)
        return json.dumps(result)

    elif action == "maintenance":
        stale_days = args.get("stale_days", 90)
        report = wiki.maintenance(stale_days=stale_days)
        return json.dumps(report, indent=2, ensure_ascii=False)

    elif action == "follow":
        title = args.get("title", "").strip()
        if not title:
            return "Error: 'title' is required for follow."
        depth = args.get("depth", 2)
        max_notes = args.get("max_notes", 10)
        include_content = args.get("include_content", False)
        result = wiki.follow(
            title, depth=depth, max_notes=max_notes, include_content=include_content
        )
        if "error" in result:
            return f"Note not found: '{title}'"
        return json.dumps(result, indent=2, ensure_ascii=False)

    elif action == "backlinks":
        title = args.get("title", "").strip()
        if not title:
            return "Error: 'title' is required for backlinks."
        results = wiki.backlinks(title)
        return json.dumps(results, indent=2, ensure_ascii=False)

    return (
        f"Error: Unknown action '{action}'. "
        "Use write, append, read, search, list, delete, rename, list_tags, rename_tag, "
        "maintenance, follow, or backlinks."
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
