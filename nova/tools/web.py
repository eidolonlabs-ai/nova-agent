"""Web search tool — search the web via DuckDuckGo HTML.

Uses DuckDuckGo's HTML interface for zero-dependency web search.
"""

import logging
import re
from html.parser import HTMLParser
from typing import Any

import httpx

from nova.tools.registry import registry

logger = logging.getLogger(__name__)

WEB_SEARCH_SCHEMA = {
    "name": "web_search",
    "description": "Search the web for information. Returns relevant results with titles, URLs, and snippets.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default: 5).",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}

_DDG_SEARCH_URL = "https://html.duckduckgo.com/html/"
_DDG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


class _DDGResultParser(HTMLParser):
    """Parse DuckDuckGo HTML search results."""

    def __init__(self):
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_result = False
        self._in_title = False
        self._in_snippet = False
        self._current: dict[str, str] = {}
        self._text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attr_dict = dict(attrs)
        cls = attr_dict.get("class") or ""
        if tag == "div" and cls == "result":
            self._in_result = True
            self._current = {}
        elif tag == "a" and self._in_result and "result__snippet" not in cls:
            href = attr_dict.get("href") or ""
            # DuckDuckGo wraps URLs with a redirect — extract the real URL
            if href.startswith("/"):
                # Extract actual URL from the redirect
                match = re.search(r"uddg=([^&]+)", href)
                if match:
                    from urllib.parse import unquote
                    href = unquote(match.group(1))
            self._current["url"] = href
        elif tag == "a" and "result__title" in cls:
            self._in_title = True
            self._text = ""
        elif tag == "a" and "result__snippet" in cls:
            self._in_snippet = True
            self._text = ""

    def handle_endtag(self, tag: str):
        if tag == "div" and self._in_result:
            if self._current.get("title") or self._current.get("url"):
                self.results.append(self._current)
            self._in_result = False
        elif tag == "a":
            if self._in_title:
                self._current["title"] = self._text.strip()
                self._in_title = False
            elif self._in_snippet:
                self._current["snippet"] = self._text.strip()
                self._in_snippet = False

    def handle_data(self, data: str):
        if self._in_title or self._in_snippet:
            self._text += data


def _web_search(args: dict[str, Any], **kwargs) -> str:
    """Search the web using DuckDuckGo HTML interface."""
    query = args.get("query", "")
    num_results = min(args.get("num_results", 5), 10)

    if not query:
        return "Error: No search query provided."

    try:
        response = httpx.post(
            _DDG_SEARCH_URL,
            data={"q": query},
            headers=_DDG_HEADERS,
            timeout=15.0,
            follow_redirects=True,
        )
        response.raise_for_status()

        parser = _DDGResultParser()
        parser.feed(response.text)

        results = parser.results[:num_results]

        if not results:
            return f"No results found for '{query}'."

        lines = [f"Search results for '{query}':\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "(no title)")
            url = r.get("url", "")
            snippet = r.get("snippet", "")
            lines.append(f"{i}. **{title}**")
            if url:
                lines.append(f"   URL: {url}")
            if snippet:
                lines.append(f"   {snippet}")
            lines.append("")

        return "\n".join(lines)

    except httpx.HTTPError as e:
        return f"Error: Web search failed: {e}"
    except Exception as e:
        return f"Error: Web search failed: {e}"


registry.register(
    name="web_search",
    toolset="web",
    schema=WEB_SEARCH_SCHEMA,
    handler=_web_search,
    emoji="🔍",
)
