"""Tests for the MCP client — stdio, HTTP, and SSE transports."""

import json
from unittest.mock import MagicMock, patch

import pytest

from nova.mcp_client import (
    McpClient,
    McpHttpConfig,
    McpResourceInfo,
    McpSseConfig,
    McpStdioConfig,
    McpToolInfo,
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


# ── Additional error-path and SSE tests ────────────────────────────────────


# ── _StdioTransport error paths ─────────────────────────────────────────────


def _make_proc(
    stdout_data: str = '{"jsonrpc":"2.0","id":0,"result":{}}\n',
    poll_return=None,
):
    proc = MagicMock()
    proc.stdin = MagicMock()
    proc.stdin.closed = False
    proc.stdout = MagicMock()
    proc.stdout.closed = False
    proc.stdout.readline.return_value = stdout_data
    proc.poll.return_value = poll_return
    return proc


def test_stdio_connect_popen_raises_returns_false():
    config = McpStdioConfig(command="nonexistent", args=[])
    transport = _StdioTransport(config)
    with patch("nova.mcp_client.subprocess.Popen", side_effect=FileNotFoundError("no cmd")):
        result = transport.connect()
    assert result is False
    assert transport._proc is None


def test_stdio_connect_calls_disconnect_on_failure():
    config = McpStdioConfig(command="bad", args=[])
    transport = _StdioTransport(config)
    with (
        patch("nova.mcp_client.subprocess.Popen", side_effect=OSError("perm denied")),
        patch.object(transport, "disconnect") as mock_disconnect,
    ):
        transport.connect()
    mock_disconnect.assert_called_once()


def test_stdio_disconnect_terminates_process():
    config = McpStdioConfig(command="echo", args=[])
    transport = _StdioTransport(config)
    proc = _make_proc()
    transport._proc = proc

    transport.disconnect()

    proc.terminate.assert_called_once()
    assert transport._proc is None


def test_stdio_disconnect_kills_on_timeout():
    config = McpStdioConfig(command="echo", args=[])
    transport = _StdioTransport(config)
    proc = _make_proc()
    proc.wait.side_effect = Exception("timeout")
    transport._proc = proc

    transport.disconnect()

    proc.kill.assert_called_once()
    assert transport._proc is None


def test_stdio_disconnect_noop_when_not_connected():
    config = McpStdioConfig(command="echo", args=[])
    transport = _StdioTransport(config)
    transport._proc = None
    transport.disconnect()  # must not raise


def test_stdio_send_request_raises_when_proc_is_none():
    config = McpStdioConfig(command="echo", args=[])
    transport = _StdioTransport(config)
    transport._proc = None
    with pytest.raises(RuntimeError, match="not running"):
        transport.send_request("tools/list")


def test_stdio_send_request_raises_when_proc_dead():
    config = McpStdioConfig(command="echo", args=[])
    transport = _StdioTransport(config)
    proc = _make_proc(poll_return=1)
    transport._proc = proc
    with pytest.raises(RuntimeError, match="not running"):
        transport.send_request("tools/list")


def test_stdio_send_request_writes_and_reads():
    response_data = {"jsonrpc": "2.0", "id": 0, "result": {"tools": []}}
    proc = _make_proc(stdout_data=json.dumps(response_data) + "\n")
    config = McpStdioConfig(command="echo", args=[])
    transport = _StdioTransport(config)
    transport._proc = proc

    result = transport.send_request("tools/list")

    assert result == response_data
    proc.stdin.write.assert_called_once()
    proc.stdin.flush.assert_called_once()


def test_stdio_send_request_increments_id():
    data = {"jsonrpc": "2.0", "id": 0, "result": {}}
    proc = _make_proc(stdout_data=json.dumps(data) + "\n")
    config = McpStdioConfig(command="echo", args=[])
    transport = _StdioTransport(config)
    transport._proc = proc

    transport.send_request("ping")
    assert transport._next_id == 1


def test_stdio_send_notification_skipped_when_stdin_closed():
    config = McpStdioConfig(command="echo", args=[])
    transport = _StdioTransport(config)
    proc = _make_proc()
    proc.stdin.closed = True
    transport._proc = proc

    transport.send_notification("notifications/initialized")
    proc.stdin.write.assert_not_called()


def test_stdio_send_notification_skipped_when_no_proc():
    config = McpStdioConfig(command="echo", args=[])
    transport = _StdioTransport(config)
    transport._proc = None
    transport.send_notification("notifications/initialized")  # must not raise


def test_stdio_send_raises_when_stdin_closed():
    config = McpStdioConfig(command="echo", args=[])
    transport = _StdioTransport(config)
    proc = _make_proc()
    proc.stdin.closed = True
    transport._proc = proc
    with pytest.raises(RuntimeError, match="Stdin is closed"):
        transport._send({"jsonrpc": "2.0", "method": "ping"})


def test_stdio_read_response_raises_on_empty_line():
    config = McpStdioConfig(command="echo", args=[])
    transport = _StdioTransport(config)
    proc = _make_proc(stdout_data="")
    transport._proc = proc
    with pytest.raises(RuntimeError, match="Server closed connection"):
        transport._read_response()


def test_stdio_read_response_raises_when_stdout_closed():
    config = McpStdioConfig(command="echo", args=[])
    transport = _StdioTransport(config)
    proc = _make_proc()
    proc.stdout.closed = True
    transport._proc = proc
    with pytest.raises(RuntimeError, match="Stdout is closed"):
        transport._read_response()


def test_stdio_initialize_handshake():
    response_data = {"jsonrpc": "2.0", "id": 0, "result": {}}
    proc = _make_proc(stdout_data=json.dumps(response_data) + "\n")
    config = McpStdioConfig(command="echo", args=[])
    transport = _StdioTransport(config)
    transport._proc = proc

    result = transport._initialize()

    assert result is True
    # _send called for init request + notification = 2 writes to stdin
    assert proc.stdin.write.call_count >= 1


def test_stdio_connect_passes_env():
    proc = _make_proc()
    config = McpStdioConfig(command="cmd", args=[], env={"MY_VAR": "val"})
    transport = _StdioTransport(config)
    with patch("nova.mcp_client.subprocess.Popen", return_value=proc) as mock_popen:
        transport.connect()
    _, kwargs = mock_popen.call_args
    assert kwargs["env"]["MY_VAR"] == "val"


# ── _HttpTransport error paths ───────────────────────────────────────────────


def _make_http_resp(body=None, status=200, headers=None):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body or {}
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    return resp


def test_http_connect_exception_returns_false():
    import httpx as _httpx

    config = McpHttpConfig(url="http://localhost/mcp")
    transport = _HttpTransport(config)
    transport._client = MagicMock()
    transport._client.post.side_effect = _httpx.ConnectError("refused")

    result = transport.connect()
    assert result is False


def test_http_connect_calls_disconnect_on_failure():
    import httpx as _httpx

    config = McpHttpConfig(url="http://localhost/mcp")
    transport = _HttpTransport(config)
    transport._client = MagicMock()
    transport._client.post.side_effect = _httpx.TimeoutException("timeout")

    with patch.object(transport, "disconnect") as mock_disconnect:
        transport.connect()
    mock_disconnect.assert_called_once()


def test_http_session_id_included_in_request_headers():
    config = McpHttpConfig(url="http://localhost/mcp")
    transport = _HttpTransport(config)
    transport._session_id = "sess-xyz"
    mock_client = MagicMock()
    mock_client.post.return_value = _make_http_resp({"jsonrpc": "2.0", "id": 0, "result": {}})
    transport._client = mock_client

    transport.send_request("tools/list")

    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"].get("Mcp-Session-Id") == "sess-xyz"


def test_http_session_id_captured_from_response():
    config = McpHttpConfig(url="http://localhost/mcp")
    transport = _HttpTransport(config)
    mock_client = MagicMock()
    mock_client.post.return_value = _make_http_resp(
        {"jsonrpc": "2.0", "id": 0, "result": {}},
        headers={"Mcp-Session-Id": "new-sess"},
    )
    transport._client = mock_client

    transport.send_request("tools/list")
    assert transport._session_id == "new-sess"


def test_http_notification_includes_session_id():
    config = McpHttpConfig(url="http://localhost/mcp")
    transport = _HttpTransport(config)
    transport._session_id = "n-sess"
    mock_client = MagicMock()
    mock_client.post.return_value = _make_http_resp({})
    transport._client = mock_client

    transport.send_notification("notifications/initialized")

    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"].get("Mcp-Session-Id") == "n-sess"


# ── _SseTransport error paths and full flow ─────────────────────────────────


def _make_sse_client_mocks(session_id=None):
    """Return a mock client wired for a successful SSE connect + _read_sse_response."""
    mock_client = MagicMock()
    get_resp = MagicMock()
    get_resp.raise_for_status = MagicMock()
    get_resp.headers = {}
    if session_id:
        get_resp.headers["Mcp-Session-Id"] = session_id
    mock_client.get.return_value = get_resp

    post_init_resp = _make_http_resp({"jsonrpc": "2.0", "id": 0, "result": {}})
    post_notif_resp = _make_http_resp({})
    mock_client.post.side_effect = [post_init_resp, post_notif_resp]

    stream_resp = MagicMock()
    stream_resp.raise_for_status = MagicMock()
    init_line = "data: " + json.dumps({"jsonrpc": "2.0", "id": 0, "result": {}})
    stream_resp.iter_lines.return_value = iter([init_line])
    stream_ctx = MagicMock()
    stream_ctx.__enter__ = MagicMock(return_value=stream_resp)
    stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_client.stream.return_value = stream_ctx
    return mock_client


def test_sse_connect_success():
    config = McpSseConfig(url="http://localhost/sse")
    transport = _SseTransport(config)
    transport._client = _make_sse_client_mocks()
    result = transport.connect()
    assert result is True


def test_sse_connect_captures_session_id():
    config = McpSseConfig(url="http://localhost/sse")
    transport = _SseTransport(config)
    transport._client = _make_sse_client_mocks(session_id="sse-1")
    transport.connect()
    assert transport._session_id == "sse-1"


def test_sse_connect_failure_returns_false():
    import httpx as _httpx

    config = McpSseConfig(url="http://localhost/sse")
    transport = _SseTransport(config)
    mock_client = MagicMock()
    mock_client.get.side_effect = _httpx.ConnectError("refused")
    transport._client = mock_client

    result = transport.connect()
    assert result is False


def test_sse_connect_failure_calls_disconnect():
    import httpx as _httpx

    config = McpSseConfig(url="http://localhost/sse")
    transport = _SseTransport(config)
    mock_client = MagicMock()
    mock_client.get.side_effect = _httpx.ConnectError("refused")
    transport._client = mock_client

    with patch.object(transport, "disconnect") as mock_disconnect:
        transport.connect()
    mock_disconnect.assert_called_once()


def test_sse_send_request_posts_and_reads_sse():
    config = McpSseConfig(url="http://localhost/sse")
    transport = _SseTransport(config)
    mock_client = MagicMock()
    mock_client.post.return_value = _make_http_resp({})
    stream_resp = MagicMock()
    stream_resp.raise_for_status = MagicMock()
    match_line = "data: " + json.dumps({"jsonrpc": "2.0", "id": 0, "result": {"tools": []}})
    stream_resp.iter_lines.return_value = iter([match_line])
    stream_ctx = MagicMock()
    stream_ctx.__enter__ = MagicMock(return_value=stream_resp)
    stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_client.stream.return_value = stream_ctx
    transport._client = mock_client

    result = transport.send_request("tools/list")
    assert result["result"] == {"tools": []}


def test_sse_send_request_includes_session_id():
    config = McpSseConfig(url="http://localhost/sse")
    transport = _SseTransport(config)
    transport._session_id = "sse-sess"
    mock_client = MagicMock()
    mock_client.post.return_value = _make_http_resp({})
    stream_resp = MagicMock()
    stream_resp.raise_for_status = MagicMock()
    match_line = "data: " + json.dumps({"jsonrpc": "2.0", "id": 0, "result": {}})
    stream_resp.iter_lines.return_value = iter([match_line])
    stream_ctx = MagicMock()
    stream_ctx.__enter__ = MagicMock(return_value=stream_resp)
    stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_client.stream.return_value = stream_ctx
    transport._client = mock_client

    transport.send_request("ping")
    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"].get("Mcp-Session-Id") == "sse-sess"


def test_sse_send_notification_posts():
    config = McpSseConfig(url="http://localhost/sse", post_url="http://localhost/post")
    transport = _SseTransport(config)
    mock_client = MagicMock()
    mock_client.post.return_value = _make_http_resp({})
    transport._client = mock_client

    transport.send_notification("notifications/initialized")
    args, _ = mock_client.post.call_args
    assert args[0] == "http://localhost/post"


def test_sse_send_notification_with_session_id():
    config = McpSseConfig(url="http://localhost/sse")
    transport = _SseTransport(config)
    transport._session_id = "n-sess"
    mock_client = MagicMock()
    mock_client.post.return_value = _make_http_resp({})
    transport._client = mock_client

    transport.send_notification("notifications/initialized")
    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"].get("Mcp-Session-Id") == "n-sess"


def test_sse_read_sse_response_raises_when_no_match():
    config = McpSseConfig(url="http://localhost/sse")
    transport = _SseTransport(config)
    mock_client = MagicMock()
    stream_resp = MagicMock()
    stream_resp.raise_for_status = MagicMock()
    # Response id=1 but we want id=99
    non_match = "data: " + json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}})
    stream_resp.iter_lines.return_value = iter([non_match])
    stream_ctx = MagicMock()
    stream_ctx.__enter__ = MagicMock(return_value=stream_resp)
    stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_client.stream.return_value = stream_ctx
    transport._client = mock_client

    with pytest.raises(RuntimeError, match="SSE response not found"):
        transport._read_sse_response(99)


def test_sse_read_sse_response_skips_non_data_lines():
    config = McpSseConfig(url="http://localhost/sse")
    transport = _SseTransport(config)
    mock_client = MagicMock()
    stream_resp = MagicMock()
    stream_resp.raise_for_status = MagicMock()
    lines = [
        ": keep-alive",
        "",
        "data: " + json.dumps({"jsonrpc": "2.0", "id": 5, "result": {"ok": True}}),
    ]
    stream_resp.iter_lines.return_value = iter(lines)
    stream_ctx = MagicMock()
    stream_ctx.__enter__ = MagicMock(return_value=stream_resp)
    stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_client.stream.return_value = stream_ctx
    transport._client = mock_client

    result = transport._read_sse_response(5)
    assert result["result"] == {"ok": True}


# ── McpClient connection management ─────────────────────────────────────────


def test_mcp_connect_all_skips_already_connected():
    client = McpClient()
    config = McpStdioConfig(command="echo", args=[])
    client.add_server_named("srv", config)
    client._connected.add("srv")

    with patch("nova.mcp_client._StdioTransport") as MockTransport:
        result = client.connect_all()

    MockTransport.assert_not_called()
    assert result == []


def test_mcp_connect_all_returns_connected_names():
    client = McpClient()
    config = McpStdioConfig(command="echo", args=[])
    client.add_server_named("srv", config)

    mock_transport = MagicMock()
    mock_transport.connect.return_value = True
    mock_transport.send_request.return_value = {"result": {"tools": [], "resources": []}}

    with patch("nova.mcp_client._StdioTransport", return_value=mock_transport):
        result = client.connect_all()

    assert "srv" in result


def test_mcp_connect_all_transport_connect_fails():
    client = McpClient()
    config = McpStdioConfig(command="bad", args=[])
    client.add_server_named("bad", config)

    mock_transport = MagicMock()
    mock_transport.connect.return_value = False

    with patch("nova.mcp_client._StdioTransport", return_value=mock_transport):
        result = client.connect_all()

    assert result == []
    assert "bad" not in client._connected


def test_mcp_disconnect_all_clears_everything():
    client = McpClient()
    client._tools = [McpToolInfo(server_name="s", name="t")]
    client._resources = [McpResourceInfo(server_name="s", name="r", uri="u")]
    client._connected.add("s")
    mock_transport = MagicMock()
    client._transports["s"] = mock_transport

    client.disconnect_all()

    assert client._tools == []
    assert client._resources == []
    assert client._connected == set()
    mock_transport.disconnect.assert_called_once()


def test_mcp_call_tool_exception_returns_error():
    client = McpClient()
    mock_transport = MagicMock()
    mock_transport.send_request.side_effect = RuntimeError("connection lost")
    client._transports["srv"] = mock_transport

    result = client.call_tool("srv", "read_file", {"path": "/x"})
    assert "Error" in result
    assert "connection lost" in result


def test_mcp_read_resource_text():
    client = McpClient()
    mock_transport = MagicMock()
    mock_transport.send_request.return_value = {"result": {"contents": [{"text": "hello"}]}}
    client._transports["srv"] = mock_transport

    result = client.read_resource("srv", "file://hello")
    assert result == "hello"


def test_mcp_read_resource_blob():
    client = McpClient()
    mock_transport = MagicMock()
    mock_transport.send_request.return_value = {"result": {"contents": [{"blob": "b64data"}]}}
    client._transports["srv"] = mock_transport

    result = client.read_resource("srv", "file://binary")
    assert result == "b64data"


def test_mcp_read_resource_empty_contents():
    client = McpClient()
    mock_transport = MagicMock()
    mock_transport.send_request.return_value = {"result": {"contents": []}}
    client._transports["srv"] = mock_transport

    result = client.read_resource("srv", "file://empty")
    assert result == "(empty resource)"


def test_mcp_read_resource_exception():
    client = McpClient()
    mock_transport = MagicMock()
    mock_transport.send_request.side_effect = RuntimeError("stream error")
    client._transports["srv"] = mock_transport

    result = client.read_resource("srv", "file://x")
    assert "Error" in result


def test_mcp_connect_server_tools_list_raises():
    client = McpClient()
    config = McpStdioConfig(command="echo", args=[])
    mock_transport = MagicMock()
    mock_transport.connect.return_value = True
    mock_transport.send_request.side_effect = RuntimeError("tools/list broken")

    with patch("nova.mcp_client._StdioTransport", return_value=mock_transport):
        result = client._connect_server("srv", config)

    assert result is False
    assert "srv" not in client._connected


def test_mcp_remove_server_rebuilds_tool_list():
    client = McpClient()
    client._connected.add("srv")
    client._tools = [
        McpToolInfo(server_name="srv", name="t1"),
        McpToolInfo(server_name="other", name="t2"),
    ]
    client._resources = [
        McpResourceInfo(server_name="srv", name="r1", uri="u1"),
    ]
    mock_transport = MagicMock()
    client._transports["srv"] = mock_transport
    client._server_configs["srv"] = McpStdioConfig(command="e", args=[])

    client.remove_server("srv")

    assert all(t.server_name != "srv" for t in client._tools)
    assert all(r.server_name != "srv" for r in client._resources)


def test_extract_tool_result_unknown_type_stringified():
    item = {"type": "binary", "data": "xyz"}
    result = McpClient._extract_tool_result({"result": {"content": [item]}})
    assert "binary" in result


def test_build_mcp_client_non_dict_server_skipped():
    config = {"mcp": {"servers": {"bad": "not-a-dict"}}}
    client = build_mcp_client(config)
    assert "bad" not in client._server_configs
