"""Shared pytest fixtures for nova-agent tests."""

import json
import tempfile
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock

import httpx
import pytest

from nova.agent import NovaAgent
from nova.session import SessionStore
from nova.wiki_memory import WikiMemory


@pytest.fixture(autouse=True)
def _mock_global_personality():
    """Auto-mock load_global_personality to prevent loading real ~/.nova/SOUL.md during tests."""
    with mock.patch("nova.prompt.load_global_personality", return_value=None):
        yield


@pytest.fixture
def minimal_config() -> dict:
    return {
        "llm": {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": "test-key",
            "model": "test-model",
        },
        "agent": {
            "max_iterations": 3,
            "temperature": 0.7,
            "top_p": 1.0,
            "identity": "You are a test agent.",
        },
        "budgets": {
            "conversation_turn_limit": 5,
            "tool_result_max_chars": 8000,
            "system_prompt_max": 8000,
        },
        "wiki": {"enabled": False},
        "session": {"directory": str(tempfile.mkdtemp())},
        "skills": {"enabled": False},
        "compression": {"enabled": False, "threshold_percent": 0.40},
        "microcompact": {"enabled": True, "keep_recent": 6},
        "context_files": [],
    }


@pytest.fixture
def delegation_config(minimal_config) -> dict:
    minimal_config["delegation"] = {
        "enabled": True,
        "max_spawn_depth": 2,
        "default_timeout_seconds": 60,
        "subagent_budgets": {"max_iterations": 30},
    }
    return minimal_config


@pytest.fixture
def mock_session_store() -> SessionStore:
    tmpdir = tempfile.mkdtemp()
    return SessionStore(Path(tmpdir) / "test.db")


@pytest.fixture
def mock_http_client() -> MagicMock:
    return MagicMock(spec=httpx.Client)


@pytest.fixture
def mock_wiki_store(tmp_path) -> WikiMemory:
    return WikiMemory(tmp_path / "wiki")


@pytest.fixture
def make_agent(minimal_config, mock_session_store, mock_http_client):
    """Factory fixture: call make_agent() or make_agent(config=...) to create a NovaAgent."""

    def _factory(config=None, session_id=None, wiki_memory_store=None):
        return NovaAgent(
            config=config or minimal_config,
            http_client=mock_http_client,
            session_store=mock_session_store,
            session_id=session_id,
            wiki_memory_store=wiki_memory_store,
        )

    return _factory


@pytest.fixture
def agent(make_agent) -> NovaAgent:
    """A ready-to-use NovaAgent with mocked dependencies."""
    return make_agent()


def mock_llm_response(status_code: int = 200, content: str = "OK", tool_calls=None) -> MagicMock:
    """Build a mock httpx.Response for an LLM API call."""
    message: dict = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    data = {"choices": [{"message": message}]}
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = data
    resp.text = json.dumps(data)
    return resp


def make_tool_call_response(tool_name: str, arguments: dict, call_id: str = "call_1") -> MagicMock:
    """Build a mock response where the LLM requests a tool call."""
    return mock_llm_response(
        content=None,
        tool_calls=[
            {
                "id": call_id,
                "type": "function",
                "function": {"name": tool_name, "arguments": json.dumps(arguments)},
            }
        ],
    )
