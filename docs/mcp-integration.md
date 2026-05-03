# MCP Integration

Nova Agent supports the Model Context Protocol (MCP) with three transport types, allowing you to connect to local and remote MCP servers.

## Transport Types

| Type | Use Case | Example |
|------|----------|---------|
| **stdio** | Local subprocess (most common) | `npx`, `python`, `uvx` |
| **http** | Streamable HTTP (remote servers) | Cloud-hosted MCP APIs |
| **sse** | Server-Sent Events (remote servers) | SSE-based MCP endpoints |

## Quick Start

Add MCP server configurations to your `config.yaml`:

```yaml
mcp:
  servers:
    # Local filesystem server (stdio)
    filesystem:
      type: stdio
      command: npx
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]

    # Remote API server (Streamable HTTP)
    remote-api:
      type: http
      url: https://api.example.com/mcp
      headers:
        Authorization: "Bearer ${API_TOKEN}"

    # SSE-based server
    sse-server:
      type: sse
      url: https://api.example.com/sse
      headers:
        Authorization: "Bearer ${API_TOKEN}"
```

## How It Works

1. **Configuration** — MCP servers are defined in `config.yaml` under `mcp.servers`
2. **Connection** — Nova connects to servers at startup using the specified transport
3. **Discovery** — Tools and resources are discovered automatically
4. **Invocation** — Discovered tools are available alongside built-in tools

## Stdio Transport (Local)

The default transport. Runs a local subprocess and communicates via stdin/stdout.

```yaml
mcp:
  servers:
    filesystem:
      type: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-filesystem"
        - "/Users/me/projects"
        - "/Users/me/documents"
      env:
        CUSTOM_VAR: "value"
```

### Configuration Fields

| Field | Required | Description |
|-------|----------|-------------|
| `type` | No | `"stdio"` (default if omitted with `command`) |
| `command` | Yes | The executable to run |
| `args` | No | Command-line arguments |
| `env` | No | Environment variables (supports `${ENV_VAR}` syntax) |

## HTTP Transport (Streamable HTTP)

For remote MCP servers that use the Streamable HTTP protocol (POST-based JSON-RPC).

```yaml
mcp:
  servers:
    github:
      type: http
      url: https://api.example.com/mcp
      headers:
        Authorization: "Bearer ${GITHUB_TOKEN}"
      timeout: 30.0
```

### Configuration Fields

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | `"http"` |
| `url` | Yes | The server endpoint URL |
| `headers` | No | HTTP headers (supports `${ENV_VAR}` syntax) |
| `timeout` | No | Request timeout in seconds (default: 30) |

### Session Management

The HTTP transport automatically captures and sends `Mcp-Session-Id` headers for session persistence across requests.

## SSE Transport (Server-Sent Events)

For MCP servers that use SSE for server→client streaming and HTTP POST for client→server.

```yaml
mcp:
  servers:
    my-sse-server:
      type: sse
      url: https://api.example.com/sse
      post_url: https://api.example.com/post  # optional, defaults to url
      headers:
        Authorization: "Bearer ${API_TOKEN}"
      timeout: 30.0
```

### Configuration Fields

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | `"sse"` |
| `url` | Yes | The SSE endpoint URL |
| `post_url` | No | POST endpoint (defaults to `url`) |
| `headers` | No | HTTP headers (supports `${ENV_VAR}` syntax) |
| `timeout` | No | Request timeout in seconds (default: 30) |

## Popular MCP Servers

| Server | Type | Command/URL | Description |
|--------|------|-------------|-------------|
| Filesystem | stdio | `npx -y @modelcontextprotocol/server-filesystem /path` | Read/write files |
| GitHub | stdio | `npx -y @modelcontextprotocol/server-github` | GitHub API access |
| PostgreSQL | stdio | `npx -y @modelcontextprotocol/server-postgres <url>` | Database queries |
| SQLite | stdio | `npx -y @modelcontextprotocol/server-sqlite <path>` | SQLite database |
| Brave Search | stdio | `npx -y @modelcontextprotocol/server-brave-search` | Web search |
| Puppeteer | stdio | `npx -y @modelcontextprotocol/server-puppeteer` | Browser automation |
| Fetch | stdio | `npx -y @modelcontextprotocol/server-fetch` | URL fetching |
| Cloud API | http | `https://api.example.com/mcp` | Remote MCP service |

See the [MCP Server Directory](https://github.com/modelcontextprotocol/servers) for more.

## Programmatic API

For custom integrations:

```python
from nova.mcp_client import (
    McpClient,
    McpStdioConfig,
    McpHttpConfig,
    McpSseConfig,
)

client = McpClient()

# Add a stdio server (local subprocess)
client.add_server(McpStdioConfig(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
))

# Add an HTTP server (Streamable HTTP)
client.add_server(McpHttpConfig(
    url="https://api.example.com/mcp",
    headers={"Authorization": "Bearer token"},
))

# Add an SSE server
client.add_server(McpSseConfig(
    url="https://api.example.com/sse",
    headers={"Authorization": "Bearer token"},
))

# Connect to all servers
connected = client.connect_all()
print(f"Connected to: {connected}")

# List discovered tools
tools = client.list_tools()
for tool in tools:
    print(f"  {tool.server_name}/{tool.name}: {tool.description}")

# Call a tool
result = client.call_tool("filesystem", "read_file", {"path": "test.txt"})

# Read a resource
content = client.read_resource("filesystem", "file:///path/to/file.txt")

# Disconnect
client.disconnect_all()
```

## Troubleshooting

### Server fails to connect

Check that the command is available:

```bash
which npx  # Should output a path
npx --version
```

For HTTP/SSE servers, verify the endpoint:

```bash
curl -v https://api.example.com/mcp
```

### Tool not appearing

Verify the server connected successfully:

```python
from nova.mcp_client import McpClient
client = McpClient()
# ... add and connect servers ...
print(client.list_tools())
```

### Environment variables

Use `${ENV_VAR}` syntax in config — these are resolved at load time:

```yaml
mcp:
  servers:
    myserver:
      type: stdio
      command: my-command
      env:
        API_KEY: "${MY_API_KEY}"
```

### HTTP session issues

The HTTP transport uses `Mcp-Session-Id` headers for session persistence. If your server doesn't support session IDs, the transport still works — it just won't send the header.
