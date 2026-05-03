"""MCP (Model Context Protocol) client — stdio, HTTP, and SSE transports.

Connects to external MCP servers, discovers tools and resources,
and exposes them as Nova-Agent tools.

Supports three transport types:
- **stdio** — Local subprocess (most common for local MCP servers)
- **http** — Streamable HTTP (POST-based JSON-RPC, newer MCP spec)
- **sse** — Server-Sent Events for server→client + HTTP POST for client→server
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Union

import httpx

logger = logging.getLogger(__name__)

# JSON-RPC protocol version
MCP_PROTOCOL_VERSION = "2024-11-05"

# Transport type alias
Transport = Union["_StdioTransport", "_HttpTransport", "_SseTransport"]


@dataclass
class McpToolInfo:
    """Metadata for an MCP-discovered tool."""

    server_name: str
    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class McpResourceInfo:
    """Metadata for an MCP-discovered resource."""

    server_name: str
    name: str
    uri: str
    description: str = ""


@dataclass
class McpStdioConfig:
    """Configuration for an MCP server via stdio transport."""

    type: str = "stdio"
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class McpHttpConfig:
    """Configuration for an MCP server via Streamable HTTP transport."""

    type: str = "http"
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0


@dataclass
class McpSseConfig:
    """Configuration for an MCP server via SSE transport."""

    type: str = "sse"
    url: str = ""
    post_url: str = ""  # Defaults to url if not set
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0


McpServerConfig = McpStdioConfig | McpHttpConfig | McpSseConfig


class _StdioTransport:
    """Manages a subprocess-based MCP connection."""

    def __init__(self, config: McpStdioConfig) -> None:
        self.config = config
        self._proc: subprocess.Popen | None = None
        self._next_id: int = 0

    def connect(self) -> bool:
        """Start the subprocess and initialize the MCP session."""
        try:
            env = {**os.environ, **self.config.env}
            self._proc = subprocess.Popen(
                [self.config.command, *self.config.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
            )
            return self._initialize()
        except Exception as e:
            logger.error("Stdio transport connect failed: %s", e)
            self.disconnect()
            return False

    def disconnect(self) -> None:
        """Terminate the subprocess."""
        if self._proc:
            try:
                if self._proc.stdin and not self._proc.stdin.closed:
                    self._proc.stdin.close()
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                self._proc.kill()
            self._proc = None

    def send_request(self, method: str, params: dict[str, Any] | None = None) -> dict:
        """Send a JSON-RPC request and read the response."""
        if not self._proc or self._proc.poll() is not None:
            raise RuntimeError("Process is not running")
        request_id = self._next_id
        self._next_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        self._send(request)
        return self._read_response()

    def send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not self._proc or not self._proc.stdin or self._proc.stdin.closed:
            return
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        self._send(notification)

    def _initialize(self) -> bool:
        """Run the MCP initialization handshake."""
        self._next_id = 0
        init_request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "nova-agent", "version": "0.1.0"},
            },
        }
        self._send(init_request)
        self._read_response()
        self.send_notification("notifications/initialized")
        return True

    def _send(self, message: dict) -> None:
        """Write a JSON-RPC message to stdin."""
        if not self._proc or not self._proc.stdin or self._proc.stdin.closed:
            raise RuntimeError("Stdin is closed")
        self._proc.stdin.write(json.dumps(message) + "\n")
        self._proc.stdin.flush()

    def _read_response(self) -> dict:
        """Read a JSON-RPC response from stdout."""
        if not self._proc or not self._proc.stdout or self._proc.stdout.closed:
            raise RuntimeError("Stdout is closed")
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError("Server closed connection")
        return json.loads(line)


class _HttpTransport:
    """Manages a Streamable HTTP-based MCP connection.

    Uses POST for all requests. The server responds with JSON-RPC
    responses directly. Supports session IDs via response headers.
    """

    def __init__(self, config: McpHttpConfig) -> None:
        self.config = config
        self._client = httpx.Client(
            base_url=config.url,
            headers=config.headers,
            timeout=config.timeout,
        )
        self._next_id: int = 0
        self._session_id: str | None = None

    def connect(self) -> bool:
        """Initialize the MCP session via HTTP."""
        try:
            return self._initialize()
        except Exception as e:
            logger.error("HTTP transport connect failed: %s", e)
            self.disconnect()
            return False

    def disconnect(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def send_request(self, method: str, params: dict[str, Any] | None = None) -> dict:
        """Send a JSON-RPC request via POST and return the response."""
        request_id = self._next_id
        self._next_id += 1
        body = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        headers = dict(self.config.headers)
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        response = self._client.post("/", json=body, headers=headers)
        response.raise_for_status()

        # Capture session ID if provided
        session_id = response.headers.get("Mcp-Session-Id")
        if session_id:
            self._session_id = session_id

        return response.json()

    def send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send a JSON-RPC notification via POST (no response expected)."""
        body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        headers = dict(self.config.headers)
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        self._client.post("/", json=body, headers=headers)

    def _initialize(self) -> bool:
        """Run the MCP initialization handshake."""
        self._next_id = 0
        init_request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "nova-agent", "version": "0.1.0"},
            },
        }
        headers = dict(self.config.headers)
        response = self._client.post("/", json=init_request, headers=headers)
        response.raise_for_status()

        # Capture session ID
        session_id = response.headers.get("Mcp-Session-Id")
        if session_id:
            self._session_id = session_id

        # Send initialized notification
        self.send_notification("notifications/initialized")
        return True


class _SseTransport:
    """Manages an SSE-based MCP connection.

    Uses Server-Sent Events for server→client messages and HTTP POST
    for client→server messages. The SSE endpoint streams JSON-RPC
    responses; the POST endpoint sends requests.
    """

    def __init__(self, config: McpSseConfig) -> None:
        self.config = config
        self._client = httpx.Client(
            base_url=config.url,
            headers=config.headers,
            timeout=config.timeout,
        )
        self._post_url = config.post_url or config.url
        self._next_id: int = 0
        self._session_id: str | None = None
        self._sse_endpoint: str | None = None

    def connect(self) -> bool:
        """Initialize the MCP session via SSE."""
        try:
            return self._initialize()
        except Exception as e:
            logger.error("SSE transport connect failed: %s", e)
            self.disconnect()
            return False

    def disconnect(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def send_request(self, method: str, params: dict[str, Any] | None = None) -> dict:
        """Send a JSON-RPC request via POST, read response from SSE stream."""
        request_id = self._next_id
        self._next_id += 1
        body = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        headers = dict(self.config.headers)
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        # POST the request
        response = self._client.post(self._post_url, json=body, headers=headers)
        response.raise_for_status()

        # For SSE, the response comes back on the SSE stream.
        # We need to read from the SSE endpoint for the matching response.
        return self._read_sse_response(request_id)

    def send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send a JSON-RPC notification via POST."""
        body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        headers = dict(self.config.headers)
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        self._client.post(self._post_url, json=body, headers=headers)

    def _initialize(self) -> bool:
        """Run the MCP initialization handshake via SSE."""
        self._next_id = 0

        # First, establish the SSE connection
        headers = dict(self.config.headers)
        headers["Accept"] = "text/event-stream"
        sse_response = self._client.get(
            "/",
            headers=headers,
            timeout=httpx.Timeout(5.0, connect=5.0),
            follow_redirects=True,
        )
        sse_response.raise_for_status()

        # Capture session ID and endpoint
        self._session_id = sse_response.headers.get("Mcp-Session-Id")
        endpoint = sse_response.headers.get("Endpoint")
        if endpoint:
            self._sse_endpoint = endpoint

        # Send initialize request via POST
        init_request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "nova-agent", "version": "0.1.0"},
            },
        }
        post_headers = dict(self.config.headers)
        if self._session_id:
            post_headers["Mcp-Session-Id"] = self._session_id

        post_response = self._client.post(
            self._post_url,
            json=init_request,
            headers=post_headers,
        )
        post_response.raise_for_status()

        # Read the initialize response from SSE
        self._read_sse_response(0)

        # Send initialized notification
        self.send_notification("notifications/initialized")
        return True

    def _read_sse_response(self, request_id: int) -> dict:
        """Read SSE events until we find the matching response."""
        # For simplicity, we make a separate GET request to read the SSE stream
        # In production, you'd maintain a persistent SSE connection with a queue
        headers = dict(self.config.headers)
        headers["Accept"] = "text/event-stream"
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        with self._client.stream("GET", "/", headers=headers) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("id") == request_id:
                        return data
        raise RuntimeError("SSE response not found for request ID")


class McpClient:
    """Manages connections to MCP servers via stdio, HTTP, or SSE transports.

    Usage:
        client = McpClient()

        # Stdio server (local subprocess)
        client.add_server(McpStdioConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"],
        ))

        # HTTP server (Streamable HTTP)
        client.add_server(McpHttpConfig(
            url="https://api.example.com/mcp",
            headers={"Authorization": "Bearer token"},
        ))

        # SSE server
        client.add_server(McpSseConfig(
            url="https://api.example.com/sse",
            headers={"Authorization": "Bearer token"},
        ))

        tools = client.list_tools()
        result = client.call_tool("filesystem", "read_file", {"path": "test.txt"})
    """

    def __init__(self) -> None:
        self._server_configs: dict[str, McpServerConfig] = {}
        self._transports: dict[str, _StdioTransport | _HttpTransport | _SseTransport] = {}
        self._tools: list[McpToolInfo] = []
        self._resources: list[McpResourceInfo] = []
        self._connected: set[str] = set()

    def add_server(self, config: McpServerConfig) -> None:
        """Register an MCP server configuration."""
        name = getattr(config, "name", f"{config.type}-{len(self._server_configs)}")
        # For stdio configs without a name, use command as name
        if isinstance(config, McpStdioConfig) and not config.command:
            name = f"stdio-{len(self._server_configs)}"
        elif isinstance(config, McpStdioConfig):
            name = config.command.split("/")[-1] or config.command
        self._server_configs[name] = config
        logger.info("Registered MCP server: %s (type=%s)", name, config.type)

    def add_server_named(self, name: str, config: McpServerConfig) -> None:
        """Register an MCP server with an explicit name."""
        self._server_configs[name] = config
        logger.info("Registered MCP server: %s (type=%s)", name, config.type)

    def remove_server(self, name: str) -> None:
        """Remove an MCP server and disconnect it."""
        self._server_configs.pop(name, None)
        self._disconnect_server(name)
        self._rebuild_tool_list()

    def connect_all(self) -> list[str]:
        """Connect to all registered servers.

        Returns:
            List of successfully connected server names.
        """
        connected = []
        for name, config in self._server_configs.items():
            if name in self._connected:
                continue
            if self._connect_server(name, config):
                connected.append(name)
        return connected

    def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for name in list(self._connected):
            self._disconnect_server(name)
        self._tools.clear()
        self._resources.clear()

    def list_tools(self) -> list[McpToolInfo]:
        """List all tools from connected servers."""
        return list(self._tools)

    def list_resources(self) -> list[McpResourceInfo]:
        """List all resources from connected servers."""
        return list(self._resources)

    def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Call an MCP tool on a specific server.

        Returns:
            Tool result as a string.
        """
        transport = self._transports.get(server_name)
        if not transport:
            return f"Error: MCP server '{server_name}' is not connected."

        try:
            response = transport.send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments,
            })
            return self._extract_tool_result(response)
        except Exception as e:
            logger.error("MCP tool call failed (%s/%s): %s", server_name, tool_name, e)
            return f"Error: MCP tool call failed: {e}"

    def read_resource(self, server_name: str, uri: str) -> str:
        """Read an MCP resource from a specific server."""
        transport = self._transports.get(server_name)
        if not transport:
            return f"Error: MCP server '{server_name}' is not connected."

        try:
            response = transport.send_request("resources/read", {"uri": uri})
            result = response.get("result", {})
            contents = result.get("contents", [])
            if contents:
                return contents[0].get("text", contents[0].get("blob", "(binary)"))
            return "(empty resource)"
        except Exception as e:
            logger.error("MCP resource read failed (%s/%s): %s", server_name, uri, e)
            return f"Error: MCP resource read failed: {e}"

    def is_connected(self, server_name: str) -> bool:
        """Check if a server is connected."""
        return server_name in self._connected

    def _connect_server(self, name: str, config: McpServerConfig) -> bool:
        """Connect to a single MCP server using the appropriate transport."""
        try:
            transport: Transport
            if isinstance(config, McpStdioConfig):
                transport = _StdioTransport(config)
            elif isinstance(config, McpHttpConfig):
                transport = _HttpTransport(config)
            elif isinstance(config, McpSseConfig):
                transport = _SseTransport(config)
            else:
                logger.error("Unknown server config type: %s", type(config))
                return False

            if not transport.connect():
                return False

            self._transports[name] = transport

            # Discover tools
            tools_response = transport.send_request("tools/list")
            for tool in tools_response.get("result", {}).get("tools", []):
                self._tools.append(McpToolInfo(
                    server_name=name,
                    name=tool["name"],
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {}),
                ))

            # Discover resources
            resources_response = transport.send_request("resources/list")
            for resource in resources_response.get("result", {}).get("resources", []):
                self._resources.append(McpResourceInfo(
                    server_name=name,
                    name=resource.get("name", resource.get("uri", "")),
                    uri=resource.get("uri", ""),
                    description=resource.get("description", ""),
                ))

            self._connected.add(name)
            logger.info(
                "Connected to MCP server '%s' (%s): %d tools, %d resources",
                name, config.type, len(self._tools), len(self._resources),
            )
            return True

        except Exception as e:
            logger.error("Failed to connect to MCP server '%s': %s", name, e)
            self._disconnect_server(name)
            return False

    def _disconnect_server(self, name: str) -> None:
        """Disconnect from a single server."""
        transport = self._transports.pop(name, None)
        if transport:
            transport.disconnect()
        self._connected.discard(name)

    def _rebuild_tool_list(self) -> None:
        """Rebuild the tool list from connected servers."""
        self._tools = [
            t for t in self._tools
            if t.server_name in self._connected
        ]
        self._resources = [
            r for r in self._resources
            if r.server_name in self._connected
        ]

    @staticmethod
    def _extract_tool_result(response: dict) -> str:
        """Extract text content from a tool call response."""
        result = response.get("result", {})
        content = result.get("content", [])
        if not content:
            return "(no output)"

        parts = []
        for item in content:
            if item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif item.get("type") == "image":
                parts.append(f"[image: {item.get('mimeType', 'unknown')}]")
            else:
                parts.append(str(item))

        return "\n".join(parts) if parts else "(no output)"


def build_mcp_client(config: dict) -> McpClient:
    """Build an MCP client from Nova-Agent config.

    Config format:
        mcp:
          servers:
            filesystem:
              type: stdio
              command: npx
              args: ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
            remote-api:
              type: http
              url: https://api.example.com/mcp
              headers:
                Authorization: "Bearer ${API_TOKEN}"
            sse-server:
              type: sse
              url: https://api.example.com/sse
              headers:
                Authorization: "Bearer ${API_TOKEN}"
    """
    client = McpClient()
    mcp_cfg = config.get("mcp", {})
    servers = mcp_cfg.get("servers", {})

    for name, server_cfg in servers.items():
        if not isinstance(server_cfg, dict):
            continue

        server_type = server_cfg.get("type", "stdio")

        if server_type == "stdio":
            command = server_cfg.get("command", "")
            if not command:
                logger.warning("MCP server '%s' has no command — skipping", name)
                continue
            client.add_server_named(name, McpStdioConfig(
                command=command,
                args=server_cfg.get("args", []),
                env=server_cfg.get("env", {}),
            ))

        elif server_type == "http":
            url = server_cfg.get("url", "")
            if not url:
                logger.warning("MCP server '%s' has no url — skipping", name)
                continue
            client.add_server_named(name, McpHttpConfig(
                url=url,
                headers=server_cfg.get("headers", {}),
                timeout=server_cfg.get("timeout", 30.0),
            ))

        elif server_type == "sse":
            url = server_cfg.get("url", "")
            if not url:
                logger.warning("MCP server '%s' has no url — skipping", name)
                continue
            client.add_server_named(name, McpSseConfig(
                url=url,
                post_url=server_cfg.get("post_url", ""),
                headers=server_cfg.get("headers", {}),
                timeout=server_cfg.get("timeout", 30.0),
            ))

        else:
            logger.warning("Unknown MCP server type '%s' for server '%s'", server_type, name)

    return client
