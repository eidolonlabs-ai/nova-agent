"""Web tools backed by the official Firecrawl Python SDK.

Covers search, scrape/batch-scrape, map, crawl, extract, file parsing,
developer search, and account usage. Requires `pip install nova-agent[web]`
and a Firecrawl API key.

Long-running operations (crawl, extract) are job-based: the tool starts the
job and returns an ID the agent polls, so the agent loop is never blocked for
minutes on a single tool call.
"""

import json
import logging
from pathlib import Path
from typing import Any

from nova.tools.firecrawl_client import (
    FirecrawlUnavailable,
    as_dict,
    budget_external,
    build_client,
    document_url,
    format_document,
    get_api_key,
    get_field,
    get_timeout,
    is_available,
    translate_error,
    validate_url,
)
from nova.tools.registry import registry

logger = logging.getLogger(__name__)

_ALLOWED_FORMATS = ("markdown", "html", "rawHtml", "links", "summary")
_MAX_SCRAPE_URLS = 10
_MAX_BATCH_WAIT = 120
_MAX_PARSE_BYTES = 20 * 1024 * 1024
_PARSE_SUFFIXES = (
    ".pdf",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ppt",
    ".html",
    ".htm",
    ".csv",
    ".txt",
    ".md",
    ".rtf",
    ".odt",
)


# ── Shared helpers ──────────────────────────────────────────────────────────


def _clamp(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(number, high))


def _formats(args: dict[str, Any]) -> list[str]:
    raw = args.get("formats")
    if not isinstance(raw, list):
        return ["markdown"]
    chosen = [f for f in raw if isinstance(f, str) and f in _ALLOWED_FORMATS]
    return chosen or ["markdown"]


def _string_list(args: dict[str, Any], key: str) -> list[str] | None:
    raw = args.get(key)
    if not isinstance(raw, list):
        return None
    values = [str(item).strip() for item in raw if str(item).strip()]
    return values or None


def _wrap_external(body: str, config: dict[str, Any] | None) -> str:
    """Label and budget attacker-controlled web content."""
    return budget_external(body, "Firecrawl", config)


def _one_page():
    """Build a PaginationConfig that fetches a single page.

    Auto-pagination would pull an entire crawl into memory; results are
    truncated to a character budget anyway.
    """
    try:
        from firecrawl.v2.types import PaginationConfig
    except ImportError:  # pragma: no cover — SDK present by this point
        return None
    return PaginationConfig(auto_paginate=False)


# ── web_search ──────────────────────────────────────────────────────────────

WEB_SEARCH_SCHEMA = {
    "name": "web_search",
    "description": (
        "Search the web. Returns titles, URLs and snippets. "
        "Set scrape_content=true to also return page markdown for each hit "
        "(slower, uses more credits). Use for current events, docs, package info."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."},
            "limit": {
                "type": "integer",
                "description": "Number of results (default: 5, max: 20).",
                "default": 5,
            },
            "sources": {
                "type": "array",
                "items": {"type": "string", "enum": ["web", "news", "images"]},
                "description": "Result types to search (default: web).",
            },
            "scrape_content": {
                "type": "boolean",
                "description": "Also scrape each result to markdown (default: false).",
                "default": False,
            },
            "include_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Restrict results to these domains.",
            },
            "exclude_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Exclude these domains from results.",
            },
        },
        "required": ["query"],
    },
}


def _format_search_group(label: str, items: list[Any]) -> list[str]:
    lines = [f"### {label}"]
    for i, item in enumerate(items, 1):
        title = get_field(item, "title") or document_url(item) or "(no title)"
        url = get_field(item, "url") or document_url(item)
        description = get_field(item, "description") or get_field(item, "snippet") or ""
        lines.append(f"{i}. **{title}**")
        if url:
            lines.append(f"   URL: {url}")
        if description:
            lines.append(f"   {description}")
        body = get_field(item, "markdown") or get_field(item, "summary")
        if body:
            lines.append("")
            lines.append(str(body))
        lines.append("")
    return lines


def _web_search(args: dict[str, Any], config: dict[str, Any] | None = None, **kwargs) -> str:
    query = str(args.get("query", "")).strip()
    if not query:
        return "Error: No search query provided."

    limit = _clamp(args.get("limit", 5), 5, 1, 20)
    sources = _string_list(args, "sources") or ["web"]
    sources = [s for s in sources if s in ("web", "news", "images")] or ["web"]

    call: dict[str, Any] = {"limit": limit, "sources": sources}
    include_domains = _string_list(args, "include_domains")
    exclude_domains = _string_list(args, "exclude_domains")
    if include_domains:
        call["include_domains"] = include_domains
    if exclude_domains:
        call["exclude_domains"] = exclude_domains

    if args.get("scrape_content"):
        try:
            from firecrawl.v2.types import ScrapeOptions

            call["scrape_options"] = ScrapeOptions(formats=["markdown"])
        except ImportError:  # pragma: no cover — SDK present by this point
            pass

    try:
        client = build_client(config)
        data = client.search(query, **call)
    except FirecrawlUnavailable as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return translate_error(exc)

    groups = [
        (label, get_field(data, label))
        for label in ("web", "news", "images")
        if get_field(data, label)
    ]
    if not groups:
        return f"No results found for '{query}'."

    lines = [f"Search results for '{query}':", ""]
    for label, items in groups:
        lines.extend(_format_search_group(label.capitalize(), list(items)))

    return _wrap_external("\n".join(lines), config)


# ── web_scrape ──────────────────────────────────────────────────────────────

WEB_SCRAPE_SCHEMA = {
    "name": "web_scrape",
    "description": (
        "Scrape one or more web pages to clean markdown. Handles JS-rendered "
        f"pages and PDFs. Pass up to {_MAX_SCRAPE_URLS} URLs to scrape in a batch. "
        "Prefer this over http_get for reading web pages."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": f"URLs to scrape (1-{_MAX_SCRAPE_URLS}).",
            },
            "formats": {
                "type": "array",
                "items": {"type": "string", "enum": list(_ALLOWED_FORMATS)},
                "description": "Output formats (default: markdown).",
            },
            "only_main_content": {
                "type": "boolean",
                "description": "Strip nav/footer/ads (default: true).",
                "default": True,
            },
            "max_age": {
                "type": "integer",
                "description": "Accept a cached result up to this many ms old (faster, cheaper).",
            },
        },
        "required": ["urls"],
    },
}


def _web_scrape(args: dict[str, Any], config: dict[str, Any] | None = None, **kwargs) -> str:
    urls = _string_list(args, "urls")
    if not urls:
        single = str(args.get("url", "")).strip()
        urls = [single] if single else None
    if not urls:
        return "Error: urls is required."
    if len(urls) > _MAX_SCRAPE_URLS:
        return f"Error: Too many URLs ({len(urls)}). Maximum is {_MAX_SCRAPE_URLS}."

    for url in urls:
        error = validate_url(url)
        if error:
            return error

    options: dict[str, Any] = {
        "formats": _formats(args),
        "only_main_content": bool(args.get("only_main_content", True)),
    }
    if args.get("max_age") is not None:
        options["max_age"] = _clamp(args.get("max_age"), 0, 0, 30 * 24 * 3600 * 1000)

    try:
        client = build_client(config)
        if len(urls) == 1:
            doc = client.scrape(urls[0], timeout=get_timeout(config) * 1000, **options)
            return _wrap_external(format_document(doc), config)

        wait = min(get_timeout(config) * 2, _MAX_BATCH_WAIT)
        job = client.batch_scrape(urls, poll_interval=2, wait_timeout=wait, **options)
    except FirecrawlUnavailable as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return translate_error(exc)

    documents = list(get_field(job, "data") or [])
    status = get_field(job, "status", "unknown")
    if not documents:
        return f"Batch scrape returned no documents (status: {status})."

    header = f"Scraped {len(documents)}/{len(urls)} URLs (status: {status})."
    if len(documents) < len(urls):
        header += " Re-run web_scrape for any URL missing below."
    body = "\n\n".join(format_document(doc) for doc in documents)
    return _wrap_external(f"{header}\n\n{body}", config)


# ── web_map ─────────────────────────────────────────────────────────────────

WEB_MAP_SCHEMA = {
    "name": "web_map",
    "description": (
        "Discover URLs on a site quickly (sitemap + link graph). "
        "Use before web_crawl to see what exists, or to find a specific page."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Site URL to map."},
            "search": {
                "type": "string",
                "description": "Only return URLs matching this term.",
            },
            "limit": {
                "type": "integer",
                "description": "Max URLs to return (default: 50, max: 500).",
                "default": 50,
            },
            "include_subdomains": {
                "type": "boolean",
                "description": "Include subdomains (default: false).",
                "default": False,
            },
        },
        "required": ["url"],
    },
}


def _web_map(args: dict[str, Any], config: dict[str, Any] | None = None, **kwargs) -> str:
    url = str(args.get("url", "")).strip()
    error = validate_url(url)
    if error:
        return error

    call: dict[str, Any] = {
        "limit": _clamp(args.get("limit", 50), 50, 1, 500),
        "include_subdomains": bool(args.get("include_subdomains", False)),
    }
    search = str(args.get("search", "")).strip()
    if search:
        call["search"] = search

    try:
        client = build_client(config)
        data = client.map(url, **call)
    except FirecrawlUnavailable as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return translate_error(exc)

    links = list(get_field(data, "links") or [])
    if not links:
        return f"No URLs found for {url}."

    lines = [f"Found {len(links)} URLs on {url}:", ""]
    for link in links:
        link_url = get_field(link, "url") or str(link)
        title = get_field(link, "title")
        lines.append(f"- {link_url}" + (f" — {title}" if title else ""))

    return _wrap_external("\n".join(lines), config)


# ── web_crawl ───────────────────────────────────────────────────────────────

WEB_CRAWL_SCHEMA = {
    "name": "web_crawl",
    "description": (
        "Crawl a whole site to markdown. Job-based and asynchronous: "
        "action='start' returns a job_id, then poll action='status'. "
        "Actions: start, status, cancel, errors. Crawls cost credits per page — "
        "always set a limit, and prefer web_map or web_scrape when you know the pages."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start", "status", "cancel", "errors"],
                "description": "Operation to perform.",
            },
            "url": {"type": "string", "description": "Start URL (action=start)."},
            "job_id": {
                "type": "string",
                "description": "Crawl job ID (action=status/cancel/errors).",
            },
            "limit": {
                "type": "integer",
                "description": "Max pages to crawl (default: 20, max: 500).",
                "default": 20,
            },
            "include_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Only crawl paths matching these regexes.",
            },
            "exclude_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Skip paths matching these regexes.",
            },
            "max_discovery_depth": {
                "type": "integer",
                "description": "Max link depth from the start URL.",
            },
            "include_content": {
                "type": "boolean",
                "description": "Include page markdown in status output (default: false).",
                "default": False,
            },
        },
        "required": ["action"],
    },
}


def _crawl_start(client: Any, args: dict[str, Any], config: dict[str, Any] | None) -> str:
    url = str(args.get("url", "")).strip()
    error = validate_url(url)
    if error:
        return error

    call: dict[str, Any] = {"limit": _clamp(args.get("limit", 20), 20, 1, 500)}
    include_paths = _string_list(args, "include_paths")
    exclude_paths = _string_list(args, "exclude_paths")
    if include_paths:
        call["include_paths"] = include_paths
    if exclude_paths:
        call["exclude_paths"] = exclude_paths
    if args.get("max_discovery_depth") is not None:
        call["max_discovery_depth"] = _clamp(args.get("max_discovery_depth"), 2, 1, 10)

    job = client.start_crawl(url, **call)
    job_id = get_field(job, "id", "")
    return (
        f"Crawl started.\njob_id: {job_id}\nurl: {url}\nlimit: {call['limit']}\n\n"
        "Poll with web_crawl(action='status', job_id=...). Crawls take from seconds "
        "to minutes; do other work between polls rather than polling in a tight loop."
    )


def _crawl_status(client: Any, args: dict[str, Any], config: dict[str, Any] | None) -> str:
    job_id = str(args.get("job_id", "")).strip()
    if not job_id:
        return "Error: job_id is required for action='status'."

    pagination = _one_page()
    job = (
        client.get_crawl_status(job_id, pagination_config=pagination)
        if pagination is not None
        else client.get_crawl_status(job_id)
    )
    status = get_field(job, "status", "unknown")
    completed = get_field(job, "completed", 0)
    total = get_field(job, "total", 0)
    credits = get_field(job, "credits_used", 0)

    lines = [
        f"Crawl {job_id}",
        f"status: {status}  pages: {completed}/{total}  credits: {credits}",
    ]
    documents = list(get_field(job, "data") or [])
    include_content = bool(args.get("include_content", False))
    if documents:
        lines.append("")
        lines.append(f"Pages ({len(documents)} in this page of results):")
        lines.append("")
        for doc in documents:
            lines.append(format_document(doc, include_body=include_content))
            lines.append("")
    elif status == "scraping":
        lines.append("")
        lines.append("No pages available yet — poll again shortly.")

    return _wrap_external("\n".join(lines), config)


def _web_crawl(args: dict[str, Any], config: dict[str, Any] | None = None, **kwargs) -> str:
    action = str(args.get("action", "")).strip().lower()
    if action not in ("start", "status", "cancel", "errors"):
        return "Error: action must be one of: start, status, cancel, errors."

    try:
        client = build_client(config)
        if action == "start":
            return _crawl_start(client, args, config)
        if action == "status":
            return _crawl_status(client, args, config)

        job_id = str(args.get("job_id", "")).strip()
        if not job_id:
            return f"Error: job_id is required for action='{action}'."
        if action == "cancel":
            cancelled = client.cancel_crawl(job_id)
            return (
                f"Crawl {job_id} cancelled." if cancelled else f"Could not cancel crawl {job_id}."
            )

        response = client.get_crawl_errors(job_id)
        errors = list(get_field(response, "errors") or [])
        blocked = list(get_field(response, "robots_blocked") or [])
        if not errors and not blocked:
            return f"Crawl {job_id}: no errors reported."
        lines = [f"Crawl {job_id} errors:"]
        for item in errors:
            data = as_dict(item)
            lines.append(f"- {data.get('url', '?')}: {data.get('error', 'unknown error')}")
        if blocked:
            lines.append("")
            lines.append("Blocked by robots.txt:")
            lines.extend(f"- {url}" for url in blocked)
        return budget_external("\n".join(lines), "Firecrawl crawl errors", config)
    except FirecrawlUnavailable as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return translate_error(exc)


# ── web_extract ─────────────────────────────────────────────────────────────

WEB_EXTRACT_SCHEMA = {
    "name": "web_extract",
    "description": (
        "Extract structured JSON from web pages using an LLM. Job-based: "
        "action='start' returns a job_id, then poll action='status'. "
        "Supply a prompt and/or a JSON schema describing the fields you want. "
        "URLs may end in /* to extract across a whole site."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start", "status"],
                "description": "Operation to perform.",
            },
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "URLs to extract from (action=start).",
            },
            "prompt": {
                "type": "string",
                "description": "What to extract, in plain language.",
            },
            "schema": {
                "type": "object",
                "description": "JSON Schema for the desired output shape.",
            },
            "job_id": {"type": "string", "description": "Extract job ID (action=status)."},
            "enable_web_search": {
                "type": "boolean",
                "description": "Let the extractor follow links beyond the given URLs.",
                "default": False,
            },
        },
        "required": ["action"],
    },
}


def _web_extract(args: dict[str, Any], config: dict[str, Any] | None = None, **kwargs) -> str:
    action = str(args.get("action", "")).strip().lower()
    if action not in ("start", "status"):
        return "Error: action must be one of: start, status."

    try:
        client = build_client(config)

        if action == "status":
            job_id = str(args.get("job_id", "")).strip()
            if not job_id:
                return "Error: job_id is required for action='status'."
            response = client.get_extract_status(job_id)
            status = get_field(response, "status", "unknown")
            lines = [f"Extract {job_id}", f"status: {status}"]
            error = get_field(response, "error")
            if error:
                lines.append(f"error: {error}")
            data = get_field(response, "data")
            if data is not None:
                lines.append("")
                lines.append(json.dumps(data, indent=2, ensure_ascii=False, default=str))
            elif status == "processing":
                lines.append("")
                lines.append("Not finished yet — poll again shortly.")
            return _wrap_external("\n".join(lines), config)

        urls = _string_list(args, "urls")
        if not urls:
            return "Error: urls is required for action='start'."
        for url in urls:
            error = validate_url(url.rstrip("*").rstrip("/"))
            if error:
                return error

        prompt = str(args.get("prompt", "")).strip()
        schema = args.get("schema")
        if not prompt and not isinstance(schema, dict):
            return "Error: Provide a prompt and/or a schema describing what to extract."

        call: dict[str, Any] = {"enable_web_search": bool(args.get("enable_web_search", False))}
        if prompt:
            call["prompt"] = prompt
        if isinstance(schema, dict):
            call["schema"] = schema

        job = client.start_extract(urls, **call)
        job_id = get_field(job, "id", "")
        return (
            f"Extract started.\njob_id: {job_id}\nurls: {', '.join(urls)}\n\n"
            "Poll with web_extract(action='status', job_id=...)."
        )
    except FirecrawlUnavailable as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return translate_error(exc)


# ── web_parse ───────────────────────────────────────────────────────────────

WEB_PARSE_SCHEMA = {
    "name": "web_parse",
    "description": (
        "Convert a LOCAL document (PDF, DOCX, XLSX, PPTX, HTML) to markdown by "
        "uploading it to Firecrawl. Use for files read_file cannot decode. "
        "Sends file contents to a third-party API — prefer local tools when possible."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the local file."},
        },
        "required": ["path"],
    },
}


def _web_parse(args: dict[str, Any], config: dict[str, Any] | None = None, **kwargs) -> str:
    raw_path = str(args.get("path", "")).strip()
    if not raw_path:
        return "Error: path is required."

    path = Path(raw_path).expanduser()
    if not path.exists():
        return f"Error: File not found: {raw_path}"
    if not path.is_file():
        return f"Error: Not a file: {raw_path}"
    if path.suffix.lower() not in _PARSE_SUFFIXES:
        return (
            f"Error: Unsupported file type '{path.suffix}'. Supported: {', '.join(_PARSE_SUFFIXES)}"
        )

    size = path.stat().st_size
    if size > _MAX_PARSE_BYTES:
        return f"Error: File too large ({size:,} bytes). Maximum is {_MAX_PARSE_BYTES:,}."

    try:
        payload = path.read_bytes()
    except OSError as exc:
        return f"Error: Could not read {raw_path}: {exc}"

    try:
        client = build_client(config)
        doc = client.parse(payload, filename=path.name)
    except FirecrawlUnavailable as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return translate_error(exc)

    body = get_field(doc, "markdown") or get_field(doc, "summary") or ""
    if not body:
        return f"Parsed {path.name} but no text content was returned."
    return budget_external(
        f"Parsed {path.name} ({size:,} bytes):\n\n{body}",
        f"Firecrawl parser ({path.name})",
        config,
    )


# ── web_dev_search ──────────────────────────────────────────────────────────

WEB_DEV_SEARCH_SCHEMA = {
    "name": "web_dev_search",
    "description": (
        "Search code, docs, issues, PRs and READMEs across GitHub repositories. "
        "Use for library usage examples, upstream bug reports, and API details "
        "that generic web search buries."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for."},
            "types": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["doc", "issue", "pull_request", "readme"],
                },
                "description": "Restrict to these content types.",
            },
            "repos": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Restrict to these repos (owner/name).",
            },
            "language": {"type": "string", "description": "Filter by primary language."},
            "min_stars": {"type": "integer", "description": "Minimum repository stars."},
            "limit": {
                "type": "integer",
                "description": "Max results (default: 5, max: 20).",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}


def _web_dev_search(args: dict[str, Any], config: dict[str, Any] | None = None, **kwargs) -> str:
    query = str(args.get("query", "")).strip()
    if not query:
        return "Error: No search query provided."

    call: dict[str, Any] = {"k": _clamp(args.get("limit", 5), 5, 1, 20)}
    types = _string_list(args, "types")
    if types:
        call["types"] = [t for t in types if t in ("doc", "issue", "pull_request", "readme")]
    repos = _string_list(args, "repos")
    if repos:
        call["repos"] = repos
    language = str(args.get("language", "")).strip()
    if language:
        call["language"] = language
    if args.get("min_stars") is not None:
        call["min_stars"] = _clamp(args.get("min_stars"), 0, 0, 1_000_000)

    try:
        client = build_client(config)
        response = client.developer_search(query, **call)
    except FirecrawlUnavailable as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return translate_error(exc)

    results = list(get_field(response, "results") or [])
    if not results:
        return f"No developer search results for '{query}'."

    lines = [f"Developer search results for '{query}':", ""]
    for i, item in enumerate(results, 1):
        data = as_dict(item)
        title = data.get("title") or data.get("path") or data.get("repo") or "(untitled)"
        lines.append(f"{i}. **{title}**")
        for key in ("repo", "url", "type"):
            if data.get(key):
                lines.append(f"   {key}: {data[key]}")
        for key in ("content", "snippet", "text", "body"):
            if data.get(key):
                lines.append("")
                lines.append(str(data[key]))
                break
        lines.append("")

    return _wrap_external("\n".join(lines), config)


# ── web_usage ───────────────────────────────────────────────────────────────

WEB_USAGE_SCHEMA = {
    "name": "web_usage",
    "description": (
        "Report remaining Firecrawl credits, token balance and concurrency limits. "
        "Check before starting a large crawl."
    ),
    "parameters": {"type": "object", "properties": {}},
}


def _web_usage(args: dict[str, Any], config: dict[str, Any] | None = None, **kwargs) -> str:
    try:
        client = build_client(config)
    except FirecrawlUnavailable as exc:
        return f"Error: {exc}"

    lines = ["Firecrawl account usage:"]
    for label, method in (
        ("credits", "get_credit_usage"),
        ("tokens", "get_token_usage"),
        ("concurrency", "get_concurrency"),
    ):
        try:
            data = as_dict(getattr(client, method)())
        except Exception as exc:
            lines.append(f"- {label}: unavailable ({type(exc).__name__})")
            continue
        if not data:
            lines.append(f"- {label}: unavailable")
            continue
        rendered = ", ".join(f"{k}={v}" for k, v in data.items() if v is not None)
        lines.append(f"- {label}: {rendered or 'unavailable'}")

    return "\n".join(lines)


# ── Registration ────────────────────────────────────────────────────────────

_TOOLS: tuple[tuple[str, dict, Any, str, bool], ...] = (
    ("web_search", WEB_SEARCH_SCHEMA, _web_search, "🔍", True),
    ("web_scrape", WEB_SCRAPE_SCHEMA, _web_scrape, "📄", True),
    ("web_map", WEB_MAP_SCHEMA, _web_map, "🗺️", True),
    ("web_crawl", WEB_CRAWL_SCHEMA, _web_crawl, "🕷️", True),
    ("web_extract", WEB_EXTRACT_SCHEMA, _web_extract, "🧬", True),
    ("web_dev_search", WEB_DEV_SEARCH_SCHEMA, _web_dev_search, "🐙", True),
    ("web_usage", WEB_USAGE_SCHEMA, _web_usage, "📊", True),
    # web_parse uploads local file contents to a third party — not read-only,
    # so it requires confirmation in "ask" mode.
    ("web_parse", WEB_PARSE_SCHEMA, _web_parse, "📎", False),
)


def register_web_tools(config: dict[str, Any] | None = None) -> None:
    """Register the Firecrawl tools if they can actually be used.

    Gating rules (all must be true):
    - web.enabled is not False in config
    - the firecrawl-py SDK is importable
    - a Firecrawl API key is configured

    The eight schemas cost ~1,700 tokens on every request, so an agent with no
    key or no SDK does not pay for tools that could only return errors.

    Called from discover_builtin_tools() with the agent's config.
    """
    web_config = (config or {}).get("web")
    if isinstance(web_config, dict) and web_config.get("enabled") is False:
        logger.debug("web.enabled is false — skipping Firecrawl tool registration")
        return

    if not is_available():
        logger.debug("firecrawl-py not installed — skipping Firecrawl tool registration")
        return

    if not get_api_key(config):
        logger.debug("No Firecrawl API key — skipping Firecrawl tool registration")
        return

    for name, schema, handler, emoji, read_only in _TOOLS:
        registry.register(
            name=name,
            toolset="web",
            schema=schema,
            handler=handler,
            emoji=emoji,
            is_read_only=read_only,
        )
    logger.debug("Registered %d Firecrawl web tools", len(_TOOLS))
