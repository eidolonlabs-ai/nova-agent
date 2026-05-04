"""HTTP client tool — make GET, POST, PUT, DELETE requests.

Supports JSON payloads, custom headers, and timeout enforcement.
Integrates with permission system to control external URLs.
"""

import json
import logging
from typing import Any

import httpx

from nova.tools.registry import registry

logger = logging.getLogger(__name__)

HTTP_GET_SCHEMA = {
    "name": "http_get",
    "description": "Make an HTTP GET request and return the response body.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to request (must start with http:// or https://).",
            },
            "headers": {
                "type": "object",
                "description": "Optional custom headers (e.g., {\"Authorization\": \"Bearer token\"}).",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30, max: 300).",
                "default": 30,
            },
        },
        "required": ["url"],
    },
}

HTTP_POST_SCHEMA = {
    "name": "http_post",
    "description": "Make an HTTP POST request with optional JSON body and return the response.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to request (must start with http:// or https://).",
            },
            "body": {
                "type": "string",
                "description": "JSON body as a string (e.g., '{\"key\": \"value\"}'). If empty, sends empty body.",
            },
            "headers": {
                "type": "object",
                "description": "Optional custom headers. Content-Type defaults to application/json if not set.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30, max: 300).",
                "default": 30,
            },
        },
        "required": ["url"],
    },
}

HTTP_PUT_SCHEMA = {
    "name": "http_put",
    "description": "Make an HTTP PUT request with optional JSON body and return the response.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to request (must start with http:// or https://).",
            },
            "body": {
                "type": "string",
                "description": "JSON body as a string. If empty, sends empty body.",
            },
            "headers": {
                "type": "object",
                "description": "Optional custom headers.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30, max: 300).",
                "default": 30,
            },
        },
        "required": ["url"],
    },
}

HTTP_DELETE_SCHEMA = {
    "name": "http_delete",
    "description": "Make an HTTP DELETE request and return the response.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to request (must start with http:// or https://).",
            },
            "headers": {
                "type": "object",
                "description": "Optional custom headers.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30, max: 300).",
                "default": 30,
            },
        },
        "required": ["url"],
    },
}

_MAX_RESPONSE_CHARS = 10000


def _validate_url(url: str) -> tuple[bool, str]:
    """Validate URL format and scheme."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return False, "URL must start with http:// or https://"
    return True, ""


def _validate_timeout(timeout: int) -> tuple[bool, str]:
    """Validate timeout value."""
    if not isinstance(timeout, int) or timeout <= 0 or timeout > 300:
        return False, "Timeout must be between 1 and 300 seconds"
    return True, ""


def _truncate_response(text: str, max_chars: int = _MAX_RESPONSE_CHARS) -> str:
    """Truncate response to fit within budget."""
    if len(text) <= max_chars:
        return text
    head = int(max_chars * 0.7)
    tail = int(max_chars * 0.2)
    return (
        f"{text[:head]}\n\n"
        f"[...{len(text) - head - tail:,} chars truncated...]\n\n"
        f"{text[-tail:]}"
    )


def _make_request(
    method: str,
    url: str,
    body: str | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> str:
    """Make an HTTP request and return formatted response."""
    # Validate URL
    valid, msg = _validate_url(url)
    if not valid:
        return f"Error: {msg}"

    # Validate timeout
    valid, msg = _validate_timeout(timeout)
    if not valid:
        return f"Error: {msg}"

    # Parse headers
    if headers is None:
        headers = {}
    else:
        # Ensure headers is dict
        if not isinstance(headers, dict):
            return "Error: Headers must be a JSON object"

    # Default User-Agent
    if "User-Agent" not in headers:
        headers["User-Agent"] = "Nova-Agent/1.0"

    # Parse body for POST/PUT
    json_body = None
    if body:
        try:
            json_body = json.loads(body)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON in body: {body}"

    # Add Content-Type header if not set and we have a body
    if json_body and "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"

    logger.info("HTTP %s to %s (timeout=%ds)", method, url[:100], timeout)

    try:
        response = httpx.request(
            method,
            url,
            json=json_body,
            headers=headers,
            timeout=float(timeout),
            follow_redirects=True,
        )

        # Log status
        logger.info("HTTP %s response: %d", method, response.status_code)

        # Collect response
        status_line = f"Status: {response.status_code}"
        headers_str = "\nHeaders:"
        for key, val in response.headers.items():
            headers_str += f"\n  {key}: {val}"

        # Try to parse as JSON; fallback to text
        try:
            body_text = json.dumps(response.json(), indent=2)
        except (json.JSONDecodeError, ValueError):
            body_text = response.text

        body_text = _truncate_response(body_text)

        return f"{status_line}{headers_str}\n\nBody:\n{body_text}"

    except httpx.TimeoutException:
        return f"Error: Request timed out after {timeout}s"
    except httpx.ConnectError as e:
        return f"Error: Connection failed: {e}"
    except httpx.HTTPError as e:
        return f"Error: HTTP request failed: {e}"
    except Exception as e:
        logger.error("HTTP request unexpected error: %s", e)
        return f"Error: HTTP request failed: {e}"


def _http_get(args: dict[str, Any], **kwargs) -> str:
    """Handler for http_get."""
    url = args.get("url", "")
    headers = args.get("headers", {})
    timeout = int(args.get("timeout", 30))
    return _make_request("GET", url, headers=headers, timeout=timeout)


def _http_post(args: dict[str, Any], **kwargs) -> str:
    """Handler for http_post."""
    url = args.get("url", "")
    body = args.get("body", "")
    headers = args.get("headers", {})
    timeout = int(args.get("timeout", 30))
    return _make_request("POST", url, body=body, headers=headers, timeout=timeout)


def _http_put(args: dict[str, Any], **kwargs) -> str:
    """Handler for http_put."""
    url = args.get("url", "")
    body = args.get("body", "")
    headers = args.get("headers", {})
    timeout = int(args.get("timeout", 30))
    return _make_request("PUT", url, body=body, headers=headers, timeout=timeout)


def _http_delete(args: dict[str, Any], **kwargs) -> str:
    """Handler for http_delete."""
    url = args.get("url", "")
    headers = args.get("headers", {})
    timeout = int(args.get("timeout", 30))
    return _make_request("DELETE", url, headers=headers, timeout=timeout)


registry.register(
    name="http_get",
    toolset="http",
    schema=HTTP_GET_SCHEMA,
    handler=_http_get,
    emoji="📡",
)

registry.register(
    name="http_post",
    toolset="http",
    schema=HTTP_POST_SCHEMA,
    handler=_http_post,
    emoji="📡",
)

registry.register(
    name="http_put",
    toolset="http",
    schema=HTTP_PUT_SCHEMA,
    handler=_http_put,
    emoji="📡",
)

registry.register(
    name="http_delete",
    toolset="http",
    schema=HTTP_DELETE_SCHEMA,
    handler=_http_delete,
    emoji="📡",
)
