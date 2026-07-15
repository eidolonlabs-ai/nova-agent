"""Tests for http_client tool."""

import json
from unittest.mock import Mock, patch

import httpx
import pytest

from nova.tools.http_client import _http_delete, _http_get, _http_post, _http_put, _is_url_safe


@pytest.fixture
def mock_httpx():
    """Fixture for mocking httpx.request."""
    with patch("nova.tools.http_client.httpx.request") as mock:
        yield mock


class TestHttpGet:
    """Tests for http_get tool."""

    def test_http_get_success(self, mock_httpx):
        """Test successful GET request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"status": "ok"}
        mock_httpx.return_value = mock_response

        result = _http_get({"url": "https://example.com/api"})
        assert "Status: 200" in result
        assert "application/json" in result

    def test_http_get_no_url(self):
        """Test GET without URL."""
        result = _http_get({"url": ""})
        assert "Error:" in result

    def test_http_get_invalid_url(self):
        """Test GET with invalid URL."""
        result = _http_get({"url": "not-a-url"})
        assert "Error:" in result

    def test_http_get_timeout(self, mock_httpx):
        """Test GET timeout."""
        mock_httpx.side_effect = httpx.TimeoutException("timeout")
        result = _http_get({"url": "https://example.com/api", "timeout": 30})
        assert "Error:" in result
        assert "timed out" in result.lower()

    def test_http_get_custom_headers(self, mock_httpx):
        """Test GET with custom headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {}
        mock_httpx.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        result = _http_get({"url": "https://example.com/api", "headers": headers})
        assert "Status: 200" in result


class TestHttpPost:
    """Tests for http_post tool."""

    def test_http_post_success(self, mock_httpx):
        """Test successful POST request."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.json.return_value = {"id": 123}
        mock_httpx.return_value = mock_response

        body = json.dumps({"name": "test"})
        result = _http_post({"url": "https://example.com/api", "body": body})
        assert "Status: 201" in result

    def test_http_post_invalid_json_body(self):
        """Test POST with invalid JSON body."""
        result = _http_post({"url": "https://example.com/api", "body": "not json"})
        assert "Error:" in result
        assert "Invalid JSON" in result

    def test_http_post_empty_body(self, mock_httpx):
        """Test POST with empty body."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.side_effect = ValueError()
        mock_response.text = ""
        mock_httpx.return_value = mock_response

        result = _http_post({"url": "https://example.com/api", "body": ""})
        assert "Status: 200" in result


class TestHttpPut:
    """Tests for http_put tool."""

    def test_http_put_success(self, mock_httpx):
        """Test successful PUT request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {"updated": True}
        mock_httpx.return_value = mock_response

        body = json.dumps({"name": "updated"})
        result = _http_put({"url": "https://example.com/api/1", "body": body})
        assert "Status: 200" in result


class TestHttpDelete:
    """Tests for http_delete tool."""

    def test_http_delete_success(self, mock_httpx):
        """Test successful DELETE request."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.headers = {}
        mock_response.json.side_effect = ValueError()
        mock_response.text = ""
        mock_httpx.return_value = mock_response

        result = _http_delete({"url": "https://example.com/api/1"})
        assert "Status: 204" in result


class TestTimeoutValidation:
    """Tests for timeout validation."""

    def test_invalid_timeout_too_high(self):
        """Test timeout exceeding max."""
        result = _http_get({"url": "https://example.com/api", "timeout": 301})
        assert "Error:" in result
        assert "timeout" in result.lower()

    def test_invalid_timeout_negative(self):
        """Test negative timeout."""
        result = _http_get({"url": "https://example.com/api", "timeout": -1})
        assert "Error:" in result


class TestSSRFProtection:
    """Tests for SSRF protection in _is_url_safe.

    The check must inspect every A record returned by getaddrinfo, not just
    the first one — that's what makes DNS rebinding attacks harder. A host
    that resolves to a mix of public and private IPs should be denied.
    """

    def test_blocks_hostname_resolving_to_private_ip(self):
        fake_info = [
            (2, 1, 6, "", ("10.0.0.5", 0)),
        ]
        with patch("nova.tools.http_client.socket.getaddrinfo", return_value=fake_info):
            ok, msg = _is_url_safe("https://evil.example.com/")
        assert ok is False
        assert "private" in msg.lower()

    def test_blocks_when_any_record_is_private(self):
        # Multi-IP host: first A record is public, second is link-local.
        # Old code that called gethostbyname() would have seen only the
        # first (public) record and let this through.
        fake_info = [
            (2, 1, 6, "", ("8.8.8.8", 0)),
            (2, 1, 6, "", ("169.254.169.254", 0)),  # AWS metadata
        ]
        with patch("nova.tools.http_client.socket.getaddrinfo", return_value=fake_info):
            ok, _ = _is_url_safe("https://rebind.example.com/")
        assert ok is False

    def test_blocks_aws_metadata_endpoint(self):
        # Direct hit, no DNS shenanigans
        ok, _ = _is_url_safe("https://169.254.169.254/latest/meta-data/")
        assert ok is False

    def test_blocks_loopback(self):
        ok, _ = _is_url_safe("http://127.0.0.1/admin")
        assert ok is False

    def test_blocks_non_http_scheme(self):
        ok, _ = _is_url_safe("file:///etc/passwd")
        assert ok is False

    def test_blocks_unresolvable_host(self):
        with patch(
            "nova.tools.http_client.socket.getaddrinfo",
            side_effect=OSError("no such host"),
        ):
            ok, msg = _is_url_safe("https://nope.invalid/")
        assert ok is False
        assert "unable to resolve" in msg.lower()
