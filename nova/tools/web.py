"""Web search tool — search the web via Firecrawl."""

import logging
import re
from html import unescape
from typing import Any

import httpx

from nova.tools.registry import registry

logger = logging.getLogger(__name__)

WEB_SEARCH_SCHEMA = {
    "name": "web_search",
    "description": (
        "Search the web for information. "
        "Returns titles, URLs, and snippets for the top results. "
        "Use for current events, documentation, package info, or anything outside training data."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default: 5, max: 10).",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}

_FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v2/search"
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities."""
    return unescape(_HTML_TAG_RE.sub("", text)).strip()


def _search_firecrawl(query: str, num_results: int, api_key: str = "") -> list[dict[str, str]]:
    """Fetch and normalize results from the Firecrawl Search API."""
    request_kwargs: dict[str, Any] = {
        "json": {"query": query, "limit": num_results},
        "timeout": 15.0,
    }
    if api_key:
        request_kwargs["headers"] = {"Authorization": f"Bearer {api_key}"}

    response = httpx.post(_FIRECRAWL_SEARCH_URL, **request_kwargs)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        return []
    if payload.get("success") is False:
        raise ValueError("Firecrawl search request failed")

    data = payload.get("data", [])
    if not isinstance(data, list):
        return []

    results: list[dict[str, str]] = []
    for item in data[:num_results]:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        title = item.get("title") or metadata.get("title") or ""
        url = item.get("url") or metadata.get("url") or ""
        snippet = (
            item.get("description") or item.get("snippet") or metadata.get("description") or ""
        )
        title = _strip_html(str(title))
        url = str(url).strip()
        snippet = _strip_html(str(snippet))
        if title or url:
            results.append({"title": title, "url": url, "snippet": snippet})

    return results


def _web_search(args: dict[str, Any], config: dict[str, Any] | None = None, **kwargs) -> str:
    """Search the web using Firecrawl."""
    query = args.get("query", "").strip()
    num_results = max(0, min(int(args.get("num_results", 5)), 10))

    if not query:
        return "Error: No search query provided."

    web_config = (config or {}).get("web", {})
    api_key = web_config.get("firecrawl_api_key", "") if isinstance(web_config, dict) else ""
    if not isinstance(api_key, str):
        api_key = ""

    try:
        results = _search_firecrawl(query, num_results, api_key)
    except httpx.HTTPError:
        logger.warning("Web search HTTP request failed")
        return "Error: Web search failed."
    except (ValueError, TypeError):
        logger.warning("Web search returned invalid data")
        return "Error: Web search returned invalid data."
    except Exception:
        logger.error("Web search unexpected error")
        return "Error: Web search failed."

    if not results:
        return f"No results found for '{query}'."

    lines = [f"Search results for '{query}':\n"]
    for i, r in enumerate(results, 1):
        title = r.get("title") or "(no title)"
        url = r.get("url", "")
        snippet = r.get("snippet", "")
        lines.append(f"{i}. **{title}**")
        if url:
            lines.append(f"   URL: {url}")
        if snippet:
            lines.append(f"   {snippet}")
        lines.append("")

    return "\n".join(lines)


registry.register(
    name="web_search",
    toolset="web",
    schema=WEB_SEARCH_SCHEMA,
    handler=_web_search,
    emoji="🔍",
)
