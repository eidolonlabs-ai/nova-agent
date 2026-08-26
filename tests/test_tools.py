"""Tests for tool handlers — terminal, file_ops, search_files, web."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nova.tools.file_ops import _patch_file, _read_file, _write_file
from nova.tools.search_files import _search_files
from nova.tools.terminal import _truncate_output, execute_terminal
from nova.tools.web import _search_firecrawl, _strip_html, _web_search

# ── Terminal Tests ──────────────────────────────────────────────────────────


def test_terminal_echo_command():
    """Test basic echo command execution."""
    result = execute_terminal({"command": "echo hello"})
    assert "hello" in result
    assert "exit code: 0" in result


def test_terminal_command_with_workdir():
    """Test command execution with working directory."""
    tmpdir = tempfile.mkdtemp()
    result = execute_terminal({"command": "pwd", "workdir": tmpdir})
    assert tmpdir in result


def test_terminal_command_timeout():
    """Test that long-running commands time out."""
    result = execute_terminal({"command": "sleep 10", "timeout": 1})
    assert "timed out" in result


def test_terminal_empty_command():
    """Test that empty command returns error."""
    result = execute_terminal({"command": ""})
    assert "Error" in result


def test_terminal_failing_command():
    """Test that failing commands return non-zero exit code."""
    result = execute_terminal({"command": "false"})
    assert "exit code: 1" in result


def test_terminal_output_truncation():
    """Test that long output is truncated."""
    # Generate a command that produces lots of output
    result = execute_terminal({"command": "python3 -c \"print('A' * 20000)\""})
    assert "truncated" in result or len(result) < 20000


def test_truncate_output_short():
    """Test that short output is not truncated."""
    output = "short output"
    result = _truncate_output(output, max_chars=100)
    assert result == output


def test_truncate_output_long():
    """Test that long output is truncated with head/tail."""
    output = "H" * 100 + "M" * 800 + "T" * 100
    result = _truncate_output(output, max_chars=100)
    assert "truncated" in result
    assert result.startswith("H")
    assert result.endswith("T")


# ── File Operations Tests ───────────────────────────────────────────────────


def test_read_file_basic():
    """Test reading a file."""
    tmpdir = Path(tempfile.mkdtemp())
    test_file = tmpdir / "test.txt"
    test_file.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")

    result = _read_file({"path": str(test_file)})
    assert "line 1" in result
    assert "line 2" in result
    assert "line 3" in result


def test_read_file_with_range():
    """Test reading a file with line range."""
    tmpdir = Path(tempfile.mkdtemp())
    test_file = tmpdir / "test.txt"
    test_file.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n", encoding="utf-8")

    result = _read_file({"path": str(test_file), "offset": 2, "limit": 2})
    assert "line 2" in result
    assert "line 3" in result
    assert "line 1" not in result
    assert "line 4" not in result


def test_read_file_nonexistent():
    """Test reading a nonexistent file."""
    result = _read_file({"path": "/nonexistent/file.txt"})
    assert "Error" in result
    assert "not found" in result


def test_write_file_basic():
    """Test writing a file."""
    tmpdir = Path(tempfile.mkdtemp())
    test_file = tmpdir / "output.txt"

    result = _write_file({"path": str(test_file), "content": "hello world"})
    assert "Written" in result or "written" in result.lower() or "success" in result.lower()
    assert test_file.read_text() == "hello world"


def test_write_file_creates_parent_dirs():
    """Test that write_file creates parent directories."""
    tmpdir = Path(tempfile.mkdtemp())
    test_file = tmpdir / "sub" / "dir" / "output.txt"

    _write_file({"path": str(test_file), "content": "nested"})
    assert test_file.exists()
    assert test_file.read_text() == "nested"


def test_patch_file_basic():
    """Test basic search/replace patch."""
    tmpdir = Path(tempfile.mkdtemp())
    test_file = tmpdir / "test.txt"
    test_file.write_text("hello world\nfoo bar\n", encoding="utf-8")

    result = _patch_file(
        {
            "path": str(test_file),
            "old_string": "hello world",
            "new_string": "goodbye world",
        }
    )
    assert "Patched" in result or "patched" in result.lower() or "success" in result.lower()
    content = test_file.read_text()
    assert "goodbye world" in content
    assert "hello world" not in content


def test_patch_file_no_match():
    """Test patch with no matching string."""
    tmpdir = Path(tempfile.mkdtemp())
    test_file = tmpdir / "test.txt"
    test_file.write_text("hello world\n", encoding="utf-8")

    result = _patch_file(
        {
            "path": str(test_file),
            "old_string": "not found",
            "new_string": "replacement",
        }
    )
    assert "Error" in result or "not found" in result.lower()


# ── Search Files Tests ──────────────────────────────────────────────────────


def test_search_files_basic():
    """Test basic file search."""
    tmpdir = Path(tempfile.mkdtemp())
    (tmpdir / "file1.py").write_text("def hello():\n    pass\n", encoding="utf-8")
    (tmpdir / "file2.py").write_text("def world():\n    pass\n", encoding="utf-8")

    result = _search_files({"pattern": "hello", "path": str(tmpdir)})
    assert "file1.py" in result
    assert "file2.py" not in result


def test_search_files_regex():
    """Test regex search mode."""
    tmpdir = Path(tempfile.mkdtemp())
    (tmpdir / "test.py").write_text("def test_foo():\n    pass\n", encoding="utf-8")

    result = _search_files(
        {
            "pattern": "def test_\\w+",
            "path": str(tmpdir),
            "mode": "regex",
        }
    )
    assert "test.py" in result


def test_search_files_with_glob():
    """Test search with glob filter."""
    tmpdir = Path(tempfile.mkdtemp())
    (tmpdir / "file.py").write_text("hello\n", encoding="utf-8")
    (tmpdir / "file.txt").write_text("hello\n", encoding="utf-8")

    result = _search_files(
        {
            "pattern": "hello",
            "path": str(tmpdir),
            "file_pattern": "*.py",
        }
    )
    assert "file.py" in result
    assert "file.txt" not in result


def test_search_files_no_results():
    """Test search with no matching results."""
    tmpdir = Path(tempfile.mkdtemp())
    (tmpdir / "file.txt").write_text("nothing here\n", encoding="utf-8")

    result = _search_files({"pattern": "notfound", "path": str(tmpdir)})
    assert "No matches" in result or "no matches" in result.lower() or "No results" in result


# ── Web Search Tests ────────────────────────────────────────────────────────

_FIRECRAWL_RESPONSE = {
    "success": True,
    "data": [
        {
            "title": "Python.org",
            "url": "https://www.python.org",
            "description": "The official home of the Python programming language.",
        },
        {
            "title": "Python & Docs",
            "url": "https://docs.python.org",
            "description": "Python <b>3.12</b> documentation.",
        },
    ],
}


def _mock_firecrawl_response(payload: object = _FIRECRAWL_RESPONSE) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_strip_html_removes_tags():
    assert _strip_html("<b>hello</b> world") == "hello world"


def test_strip_html_unescapes_entities():
    assert _strip_html("Python &amp; Docs") == "Python & Docs"


def test_strip_html_empty():
    assert _strip_html("") == ""


def test_search_firecrawl_posts_payload_and_authenticates():
    with patch("nova.tools.web.httpx.post", return_value=_mock_firecrawl_response()) as post:
        results = _search_firecrawl("python", 5, "firecrawl-secret")

    post.assert_called_once_with(
        "https://api.firecrawl.dev/v2/search",
        json={"query": "python", "limit": 5},
        headers={"Authorization": "Bearer firecrawl-secret"},
        timeout=15.0,
    )
    assert results[0] == {
        "title": "Python.org",
        "url": "https://www.python.org",
        "snippet": "The official home of the Python programming language.",
    }


def test_search_firecrawl_allows_anonymous_requests():
    with patch("nova.tools.web.httpx.post", return_value=_mock_firecrawl_response()) as post:
        _search_firecrawl("python", 5)

    assert "headers" not in post.call_args.kwargs


def test_search_firecrawl_parses_current_response_and_strips_html():
    with patch("nova.tools.web.httpx.post", return_value=_mock_firecrawl_response()):
        results = _search_firecrawl("python", 5)

    assert len(results) == 2
    assert results[1]["title"] == "Python & Docs"
    assert "<b>" not in results[1]["snippet"]
    assert "3.12" in results[1]["snippet"]


def test_search_firecrawl_returns_empty_for_missing_or_empty_data():
    for payload in ({}, {"success": True, "data": []}):
        with patch("nova.tools.web.httpx.post", return_value=_mock_firecrawl_response(payload)):
            assert _search_firecrawl("python", 5) == []


def test_search_firecrawl_raises_for_api_failure():
    with (
        patch(
            "nova.tools.web.httpx.post",
            return_value=_mock_firecrawl_response({"success": False, "error": "bad secret"}),
        ),
        pytest.raises(ValueError, match="request failed"),
    ):
        _search_firecrawl("python", 5)


def test_search_firecrawl_propagates_http_failure():
    import httpx as _httpx

    response = _mock_firecrawl_response()
    response.raise_for_status.side_effect = _httpx.HTTPStatusError(
        "bad status", request=MagicMock(), response=response
    )
    with (
        patch("nova.tools.web.httpx.post", return_value=response),
        pytest.raises(_httpx.HTTPError),
    ):
        _search_firecrawl("python", 5)


def test_web_search_passes_configured_api_key():
    with patch("nova.tools.web._search_firecrawl", return_value=[]) as search:
        _web_search({"query": "python"}, config={"web": {"firecrawl_api_key": "secret"}})

    search.assert_called_once_with("python", 5, "secret")


def test_web_search_formats_output():
    with patch(
        "nova.tools.web._search_firecrawl",
        return_value=[
            {"title": "Python.org", "url": "https://www.python.org", "snippet": "Official site."},
        ],
    ):
        result = _web_search({"query": "python"})

    assert "Python.org" in result
    assert "https://www.python.org" in result
    assert "Official site." in result
    assert "1." in result


def test_web_search_empty_query():
    result = _web_search({"query": ""})
    assert "Error" in result


def test_web_search_no_results():
    with patch("nova.tools.web._search_firecrawl", return_value=[]):
        result = _web_search({"query": "xyzzy12345"})

    assert "No results" in result


def test_web_search_clamps_num_results():
    captured = {}

    def fake_search(query, num_results, api_key=""):
        captured["num_results"] = num_results
        return []

    with patch("nova.tools.web._search_firecrawl", side_effect=fake_search):
        _web_search({"query": "test", "num_results": 999})

    assert captured["num_results"] == 10


def test_web_search_handles_http_error_without_exposing_api_key():
    import httpx as _httpx

    with patch("nova.tools.web._search_firecrawl", side_effect=_httpx.HTTPError("timeout")):
        result = _web_search({"query": "test"}, config={"web": {"firecrawl_api_key": "secret"}})

    assert "Error" in result
    assert "secret" not in result


def test_web_search_handles_api_error_without_exposing_api_key():
    with patch("nova.tools.web._search_firecrawl", side_effect=ValueError("request failed")):
        result = _web_search({"query": "test"}, config={"web": {"firecrawl_api_key": "secret"}})

    assert "Error" in result
    assert "secret" not in result
