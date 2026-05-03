"""Web search tool — search the web via Bing RSS.

Uses Bing's RSS feed for zero-dependency, zero-API-key web search.
The RSS endpoint returns structured XML that is far more reliable than
scraping HTML search pages, which are subject to bot-detection blocks.
"""

import logging
import re
from html import unescape
from typing import Any
from xml.etree import ElementTree as ET

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

_BING_RSS_URL = "https://www.bing.com/search"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# Strip HTML tags from Bing RSS description snippets
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities."""
    return unescape(_HTML_TAG_RE.sub("", text)).strip()


def _search_bing_rss(query: str, num_results: int) -> list[dict[str, str]]:
    """Fetch results from Bing RSS feed. Returns list of {title, url, snippet}."""
    response = httpx.get(
        _BING_RSS_URL,
        params={"q": query, "format": "rss"},
        headers=_HEADERS,
        timeout=15.0,
        follow_redirects=True,
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    channel = root.find("channel")
    if channel is None:
        return []

    def _text(el: ET.Element, tag: str) -> str:
        """Extract all text from a child element, including text inside child tags."""
        child = el.find(tag)
        if child is None:
            return ""
        return ET.tostring(child, encoding="unicode", method="text")

    results = []
    for item in channel.findall("item")[:num_results]:
        title = _strip_html(_text(item, "title"))
        url = (item.findtext("link") or "").strip()
        snippet = _strip_html(_text(item, "description"))
        if title or url:
            results.append({"title": title, "url": url, "snippet": snippet})

    return results


def _web_search(args: dict[str, Any], **kwargs) -> str:
    """Search the web using Bing RSS."""
    query = args.get("query", "").strip()
    num_results = min(int(args.get("num_results", 5)), 10)

    if not query:
        return "Error: No search query provided."

    try:
        results = _search_bing_rss(query, num_results)
    except ET.ParseError as e:
        logger.warning("Web search XML parse error: %s", e)
        return f"Error: Web search returned malformed data: {e}"
    except httpx.HTTPError as e:
        logger.warning("Web search HTTP error: %s", e)
        return f"Error: Web search failed: {e}"
    except Exception as e:
        logger.error("Web search unexpected error: %s", e)
        return f"Error: Web search failed: {e}"

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
