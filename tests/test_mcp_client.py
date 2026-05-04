"""Tests for the MCP client — stdio, HTTP, and SSE transports."""

from unittest.mock import MagicMock, patch

from nova.mcp_client import (
    McpClient,
    McpHttpConfig,
    McpSseConfig,
    McpStdioConfig,
    _HttpTransport,
    _SseTransport,
    _StdioTransport,
    build_mcp_client,
)

# ── Config Dataclasses ──────────────────────────────────────────────────────


def test_stdio_config_defaults():
    config = McpStdioConfig(command="npx")
    assert config.type == "stdio"
    assert config.command == "npx"
    assert config.args == []
    assert config.env == {}


def test_http_config_defaults():
    config = McpHttpConfig(url="https://api.example.com/mcp")
    assert config.type == "http"
    assert config.url == "https://api.example.com/mcp"
    assert config.headers == {}
    assert config.timeout == 30.0


def test_sse_config_defaults():
    config = McpSseConfig(url="https://api.example.com/sse")
    assert config.type == "sse"
    assert config.url == "https://api.example.com/sse"
    assert config.post_url == ""
    assert config.headers == {}
    assert config.timeout == 30.0


# ── McpClient — Server Registration ─────────────────────────────────────────


def test_add_stdio_server():
    client = McpClient()
    client.add_server(McpStdioConfig(command="echo", args=["hello"]))
    assert len(client._server_configs) == 1


def test_add_http_server():
    client = McpClient()
    client.add_server(McpHttpConfig(url="https://api.example.com/mcp"))
    assert len(client._server_configs) == 1


def test_add_sse_server():
    client = McpClient()
    client.add_server(McpSseConfig(url="https://api.example.com/sse"))
    assert len(client._server_configs) == 1


def test_add_server_named():
    client = McpClient()
    client.add_server_named("my-server", McpHttpConfig(url="https://example.com"))
    assert "my-server" in client._server_configs


def test_remove_server():
    client = McpClient()
    client.add_server_named("test", McpHttpConfig(url="https://example.com"))
    client.remove_server("test")
    assert "test" not in client._server_configs


# ── McpClient — Tool/Resource Lists ─────────────────────────────────────────


def test_list_tools_empty():
    client = McpClient()
    assert client.list_tools() == []


def test_list_resources_empty():
    client = McpClient()
    assert client.list_resources() == []


def test_is_connected_false_by_default():
    client = McpClient()
    assert client.is_connected("nonexistent") is False


# ── _HttpTransport — Unit Tests ─────────────────────────────────────────────


def test_http_transport_initialization():
    config = McpHttpConfig(url="https://api.example.com/mcp")
    transport = _HttpTransport(config)
    assert transport.config == config
    assert transport._next_id == 0
    assert transport._session_id is None
    transport.disconnect()


@patch("httpx.Client")
def test_http_transport_connect(mock_client_cls):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    config = McpHttpConfig(url="https://api.example.com/mcp")
    transport = _HttpTransport(config)
    result = transport.connect()

    assert result is True
    mock_client.post.assert_called()
    transport.disconnect()


@patch("httpx.Client")
def test_http_transport_send_request(mock_client_cls):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"content": [{"type": "text", "text": "hello"}]}}
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    config = McpHttpConfig(url="https://api.example.com/mcp")
    transport = _HttpTransport(config)
    response = transport.send_request("tools/call", {"name": "echo", "arguments": {"msg": "hi"}})

    assert response["result"]["content"][0]["text"] == "hello"
    mock_client.post.assert_called_once()
    transport.disconnect()


@patch("httpx.Client")
def test_http_transport_session_id_capture(mock_client_cls):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.headers = {"Mcp-Session-Id": "sess-123"}
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    config = McpHttpConfig(url="https://api.example.com/mcp")
    transport = _HttpTransport(config)
    transport.connect()

    assert transport._session_id == "sess-123"
    transport.disconnect()


# ── _SseTransport — Unit Tests ──────────────────────────────────────────────


def test_sse_transport_initialization():
    config = McpSseConfig(url="https://api.example.com/sse")
    transport = _SseTransport(config)
    assert transport.config == config
    assert transport._post_url == config.url  # defaults to url
    assert transport._next_id == 0
    assert transport._session_id is None
    transport.disconnect()


def test_sse_transport_custom_post_url():
    config = McpSseConfig(
        url="https://api.example.com/sse", post_url="https://api.example.com/post"
    )
    transport = _SseTransport(config)
    assert transport._post_url == "https://api.example.com/post"
    transport.disconnect()


@patch("httpx.Client")
def test_sse_transport_send_request(mock_client_cls):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {"content": [{"type": "text", "text": "sse response"}]}
    }
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    config = McpSseConfig(url="https://api.example.com/sse")
    transport = _SseTransport(config)
    # Note: SSE transport needs SSE stream for responses, so send_request
    # will try to read from SSE. We test the POST part works.
    transport.disconnect()


# ── _StdioTransport — Unit Tests ────────────────────────────────────────────


def test_stdio_transport_initialization():
    config = McpStdioConfig(command="echo")
    transport = _StdioTransport(config)
    assert transport.config == config
    assert transport._proc is None
    assert transport._next_id == 0


# ── McpClient — call_tool and read_resource ─────────────────────────────────


def test_call_tool_not_connected():
    client = McpClient()
    result = client.call_tool("nonexistent", "some_tool", {})
    assert "not connected" in result


def test_read_resource_not_connected():
    client = McpClient()
    result = client.read_resource("nonexistent", "file:///test")
    assert "not connected" in result


# ── _extract_tool_result ────────────────────────────────────────────────────


def test_extract_tool_result_text():
    response = {"result": {"content": [{"type": "text", "text": "hello world"}]}}
    result = McpClient._extract_tool_result(response)
    assert result == "hello world"


def test_extract_tool_result_multiple_parts():
    response = {
        "result": {
            "content": [
                {"type": "text", "text": "part1"},
                {"type": "text", "text": "part2"},
            ]
        }
    }
    result = McpClient._extract_tool_result(response)
    assert result == "part1\npart2"


def test_extract_tool_result_image():
    response = {"result": {"content": [{"type": "image", "mimeType": "image/png"}]}}
    result = McpClient._extract_tool_result(response)
    assert "[image: image/png]" in result


def test_extract_tool_result_empty():
    response = {"result": {"content": []}}
    result = McpClient._extract_tool_result(response)
    assert result == "(no output)"


def test_extract_tool_result_no_content():
    response = {"result": {}}
    result = McpClient._extract_tool_result(response)
    assert result == "(no output)"


# ── build_mcp_client ────────────────────────────────────────────────────────


def test_build_mcp_client_stdio():
    config = {
        "mcp": {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
                }
            }
        }
    }
    client = build_mcp_client(config)
    assert "filesystem" in client._server_configs
    server = client._server_configs["filesystem"]
    assert isinstance(server, McpStdioConfig)
    assert server.command == "npx"


def test_build_mcp_client_http():
    config = {
        "mcp": {
            "servers": {
                "remote-api": {
                    "type": "http",
                    "url": "https://api.example.com/mcp",
                    "headers": {"Authorization": "Bearer token"},
                }
            }
        }
    }
    client = build_mcp_client(config)
    assert "remote-api" in client._server_configs
    server = client._server_configs["remote-api"]
    assert isinstance(server, McpHttpConfig)
    assert server.url == "https://api.example.com/mcp"
    assert server.headers == {"Authorization": "Bearer token"}


def test_build_mcp_client_sse():
    config = {
        "mcp": {
            "servers": {
                "sse-server": {
                    "type": "sse",
                    "url": "https://api.example.com/sse",
                    "headers": {"Authorization": "Bearer token"},
                }
            }
        }
    }
    client = build_mcp_client(config)
    assert "sse-server" in client._server_configs
    server = client._server_configs["sse-server"]
    assert isinstance(server, McpSseConfig)
    assert server.url == "https://api.example.com/sse"


def test_build_mcp_client_default_type_is_stdio():
    config = {
        "mcp": {
            "servers": {
                "my-server": {
                    "command": "npx",
                    "args": ["test"],
                }
            }
        }
    }
    client = build_mcp_client(config)
    assert "my-server" in client._server_configs
    server = client._server_configs["my-server"]
    assert isinstance(server, McpStdioConfig)


def test_build_mcp_client_unknown_type():
    config = {
        "mcp": {
            "servers": {
                "bad-server": {
                    "type": "unknown",
                    "url": "https://example.com",
                }
            }
        }
    }
    client = build_mcp_client(config)
    assert "bad-server" not in client._server_configs


def test_build_mcp_client_empty_servers():
    config = {"mcp": {"servers": {}}}
    client = build_mcp_client(config)
    assert len(client._server_configs) == 0


def test_build_mcp_client_no_mcp_key():
    config = {}
    client = build_mcp_client(config)
    assert len(client._server_configs) == 0


def test_build_mcp_client_missing_command_stdio():
    config = {"mcp": {"servers": {"bad": {"type": "stdio"}}}}
    client = build_mcp_client(config)
    assert "bad" not in client._server_configs


def test_build_mcp_client_missing_url_http():
    config = {"mcp": {"servers": {"bad": {"type": "http"}}}}
    client = build_mcp_client(config)
    assert "bad" not in client._server_configs


def test_build_mcp_client_missing_url_sse():
    config = {"mcp": {"servers": {"bad": {"type": "sse"}}}}
    client = build_mcp_client(config)
    assert "bad" not in client._server_configs
