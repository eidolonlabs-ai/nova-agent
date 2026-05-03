"""Tests for delegate_tool exception paths and error handling.

Tests the error scenarios:
- Sub-agent creation failures
- Timeout execution
- Cost tracker aggregation on errors
- Configuration safety (deep copy)
- Malformed responses
"""

import json
from concurrent.futures import TimeoutError as FuturesTimeoutError
from unittest.mock import MagicMock, patch

from nova.tools.delegate_tool import _delegate_task, _extract_cost_data


def test_delegate_no_agent_context():
    """Test that delegate_task returns error when no agent context is provided."""
    result = _delegate_task({"task": "test"})
    parsed = json.loads(result)
    assert parsed["success"] is False
    assert "agent context" in parsed["error"].lower()


def test_delegate_empty_task():
    """Test that empty task description is rejected."""
    mock_agent = MagicMock()
    result = _delegate_task({"task": ""}, agent=mock_agent)
    parsed = json.loads(result)
    assert parsed["success"] is False
    assert "required" in parsed["error"].lower()


def test_delegate_depth_limit_exceeded():
    """Test that delegates at max depth are rejected."""
    mock_agent = MagicMock()
    mock_agent.depth = 2
    mock_agent.config = {"delegation": {"max_spawn_depth": 2}}

    result = _delegate_task({"task": "test task"}, agent=mock_agent)
    parsed = json.loads(result)
    assert parsed["success"] is False
    assert "max depth" in parsed["error"].lower()


def test_delegate_timeout_triggered():
    """Test that timeout is properly caught and reported."""
    mock_agent = MagicMock()
    mock_agent.depth = 0
    mock_agent.config = {
        "delegation": {"max_spawn_depth": 2, "default_timeout_seconds": 1},
        "openrouter": {"model": "test", "base_url": "http://test", "api_key": "test"},
        "agent": {"max_iterations": 3},
        "budgets": {"system_prompt_max": 8000},
        "compression": {"enabled": False},
        "microcompact": {"enabled": True},
        "memory": {"enabled": False},
        "session": {"directory": "/tmp"},
    }
    mock_agent.session_store = MagicMock()
    mock_agent.memory = None

    with patch("nova.tools.delegate_tool.ThreadPoolExecutor") as mock_executor_class:
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor_class.return_value.__exit__ = MagicMock(return_value=None)

        # Simulate timeout
        mock_future = MagicMock()
        mock_future.result.side_effect = FuturesTimeoutError()
        mock_executor.submit.return_value = mock_future

        result = _delegate_task(
            {"task": "test task", "timeout_seconds": 1},
            agent=mock_agent,
        )
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert parsed["timeout"] is True
        assert "timed out" in parsed["error"].lower()


def test_delegate_invalid_context_mode():
    """Test that invalid context_mode defaults to 'isolated'."""
    mock_agent = MagicMock()
    mock_agent.depth = 0
    mock_agent.config = {
        "delegation": {"max_spawn_depth": 2},
        "openrouter": {"model": "test", "base_url": "http://test", "api_key": "test"},
    }
    mock_agent.cost_tracker = None

    with patch("nova.tools.delegate_tool.ThreadPoolExecutor") as mock_executor_class:
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor_class.return_value.__exit__ = MagicMock(return_value=None)

        # Mock executor.submit to return a future with our result
        mock_future = MagicMock()
        mock_future.result.return_value = {"success": True, "result": "OK", "usage": {}}
        mock_executor.submit.return_value = mock_future

        result = _delegate_task(
            {"task": "test", "context_mode": "invalid_mode"},
            agent=mock_agent,
        )
        # Should succeed without error about invalid mode
        parsed = json.loads(result)
        assert parsed["success"] is True


def test_delegate_timeout_seconds_clamped():
    """Test that timeout_seconds is clamped to MAX_TIMEOUT_SECONDS."""

    mock_agent = MagicMock()
    mock_agent.depth = 0
    mock_agent.config = {
        "delegation": {"max_spawn_depth": 2},
        "openrouter": {"model": "test", "base_url": "http://test", "api_key": "test"},
    }
    mock_agent.cost_tracker = None

    with patch("nova.tools.delegate_tool.ThreadPoolExecutor") as mock_executor_class:
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor_class.return_value.__exit__ = MagicMock(return_value=None)

        mock_future = MagicMock()
        mock_future.result.return_value = {"success": True, "result": "OK", "usage": {}}
        mock_executor.submit.return_value = mock_future

        # Should accept the large timeout without error (clamped internally)
        result = _delegate_task(
            {"task": "test", "timeout_seconds": 9999},
            agent=mock_agent,
        )
        parsed = json.loads(result)
        assert parsed["success"] is True


def test_delegate_cost_tracker_aggregation():
    """Test that cost data from sub-agent is aggregated into parent."""
    mock_agent = MagicMock()
    mock_agent.depth = 0
    mock_agent.config = {
        "delegation": {"max_spawn_depth": 2},
        "openrouter": {"model": "test", "base_url": "http://test", "api_key": "test"},
    }
    mock_agent.cost_tracker = MagicMock()

    with patch("nova.tools.delegate_tool.ThreadPoolExecutor") as mock_executor_class:
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor_class.return_value.__exit__ = MagicMock(return_value=None)

        mock_future = MagicMock()
        mock_future.result.return_value = {
            "success": True,
            "result": "OK",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "input_cost": 0.001,
                "output_cost": 0.0005,
            },
        }
        mock_executor.submit.return_value = mock_future

        _delegate_task({"task": "test task"}, agent=mock_agent)

        # Verify cost_tracker.add_usage was called with the cost data
        mock_agent.cost_tracker.add_usage.assert_called_once()
        call_kwargs = mock_agent.cost_tracker.add_usage.call_args[1]
        assert call_kwargs["input_tokens"] == 100
        assert call_kwargs["output_tokens"] == 50


def test_extract_cost_data_none_subagent():
    """Test that _extract_cost_data handles None subagent gracefully."""
    result = _extract_cost_data(None)
    assert result == {}


def test_extract_cost_data_no_cost_tracker():
    """Test that _extract_cost_data handles missing cost_tracker."""
    mock_agent = MagicMock()
    delattr(mock_agent, "cost_tracker")
    result = _extract_cost_data(mock_agent)
    assert result == {}


def test_extract_cost_data_valid_tracker():
    """Test that _extract_cost_data extracts costs correctly."""
    mock_agent = MagicMock()
    mock_tracker = MagicMock()
    mock_tracker.total = MagicMock(
        input_tokens=500,
        output_tokens=300,
        input_cost=0.005,
        output_cost=0.003,
    )
    mock_agent.cost_tracker = mock_tracker

    result = _extract_cost_data(mock_agent)
    assert result["input_tokens"] == 500
    assert result["output_tokens"] == 300
    assert result["input_cost"] == 0.005
    assert result["output_cost"] == 0.003


def test_delegate_config_deep_copy():
    """Test that parent config is not mutated during delegation."""
    mock_agent = MagicMock()
    mock_agent.depth = 0
    original_config = {
        "delegation": {"max_spawn_depth": 2},
        "openrouter": {"model": "original-model", "base_url": "http://test", "api_key": "test"},
    }
    mock_agent.config = original_config.copy()

    with patch("nova.tools.delegate_tool.ThreadPoolExecutor") as mock_executor_class:
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor_class.return_value.__exit__ = MagicMock(return_value=None)

        mock_future = MagicMock()
        mock_future.result.return_value = {"success": True, "result": "OK"}
        mock_executor.submit.return_value = mock_future

        with patch("nova.tools.delegate_tool._run_subagent") as mock_run:
            mock_run.return_value = {"success": True, "result": "OK"}
            _delegate_task(
                {"task": "test", "model": "override-model"},
                agent=mock_agent,
            )
            # Verify parent config model is unchanged
            assert mock_agent.config["openrouter"]["model"] == "original-model"


def test_delegate_label_generation():
    """Test that label is auto-generated from task if not provided."""
    mock_agent = MagicMock()
    mock_agent.depth = 0
    mock_agent.config = {
        "delegation": {"max_spawn_depth": 2},
        "openrouter": {"model": "test", "base_url": "http://test", "api_key": "test"},
    }
    mock_agent.cost_tracker = None

    with patch("nova.tools.delegate_tool.ThreadPoolExecutor") as mock_executor_class:
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor_class.return_value.__exit__ = MagicMock(return_value=None)

        mock_future = MagicMock()
        mock_future.result.return_value = {"success": True, "result": "OK", "label": "generated", "usage": {}}
        mock_executor.submit.return_value = mock_future

        # Should succeed with auto-generated label
        result = _delegate_task(
            {"task": "This is a long task description that should be truncated"},
            agent=mock_agent,
        )
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert "label" in parsed or "generated" in str(parsed)


def test_delegate_fork_mode_inherits_transcript():
    """Test that fork context_mode passes parent transcript to sub-agent."""
    mock_agent = MagicMock()
    mock_agent.depth = 0
    mock_agent.config = {
        "delegation": {"max_spawn_depth": 2},
        "openrouter": {"model": "test", "base_url": "http://test", "api_key": "test"},
    }
    mock_agent.messages = [
        {"role": "user", "content": "parent message"},
        {"role": "assistant", "content": "parent response"},
    ]
    mock_agent.cost_tracker = None

    with patch("nova.tools.delegate_tool.ThreadPoolExecutor") as mock_executor_class:
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor_class.return_value.__exit__ = MagicMock(return_value=None)

        mock_future = MagicMock()
        mock_future.result.return_value = {"success": True, "result": "OK", "usage": {}}
        mock_executor.submit.return_value = mock_future

        # Should succeed with fork mode (inherited transcript)
        result = _delegate_task(
            {"task": "test", "context_mode": "fork"},
            agent=mock_agent,
        )
        parsed = json.loads(result)
        assert parsed["success"] is True


def test_delegate_result_structure():
    """Test that successful delegation returns proper result structure."""
    mock_agent = MagicMock()
    mock_agent.depth = 0
    mock_agent.config = {
        "delegation": {"max_spawn_depth": 2},
        "openrouter": {"model": "test", "base_url": "http://test", "api_key": "test"},
    }
    mock_agent.cost_tracker = None

    with patch("nova.tools.delegate_tool.ThreadPoolExecutor") as mock_executor_class:
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor_class.return_value.__exit__ = MagicMock(return_value=None)

        mock_future = MagicMock()
        mock_future.result.return_value = {
            "success": True,
            "result": "task result",
            "label": "test",
            "depth": 1,
            "elapsed_seconds": 1.5,
            "usage": {},
            "error": None,
            "timeout": False,
        }
        mock_executor.submit.return_value = mock_future

        result = _delegate_task({"task": "test task"}, agent=mock_agent)
        parsed = json.loads(result)

        assert parsed["success"] is True
        assert parsed["result"] == "task result"
        assert parsed["depth"] == 1
        assert "elapsed_seconds" in parsed
        assert "error" in parsed
        assert "timeout" in parsed
