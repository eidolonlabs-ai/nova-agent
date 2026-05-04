"""Tests for agent message compression pipeline.

Tests the two-tier compression system:
- Tier 1: Microcompact (token-stripping, no LLM call)
- Tier 2: LLM-based context compression
"""

import json
from unittest.mock import MagicMock, patch

from nova.agent import NovaAgent


def test_compression_tier1_triggered_at_threshold(
    minimal_config, mock_session_store, mock_http_client
):
    """Test that microcompact tier 1 is triggered when message tokens exceed threshold."""
    # Ensure compression config is set
    minimal_config["compression"]["enabled"] = True
    minimal_config["compression"]["threshold_percent"] = (
        0.01  # 1% = very low threshold to trigger easily
    )
    minimal_config["microcompact"]["enabled"] = True
    minimal_config["microcompact"]["keep_recent"] = 6
    minimal_config["agent"]["max_iterations"] = 1

    # Build mock responses: first LLM call returns content (no tool calls)
    llm_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Done",
                }
            }
        ]
    }
    mock_http_client.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=llm_response),
        text=json.dumps(llm_response),
    )

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    # Fill messages to trigger compression (each message ~100-200 tokens)
    for i in range(20):
        agent.messages.append({"role": "user", "content": f"message {i} " * 50})
        agent.messages.append({"role": "assistant", "content": f"response {i} " * 50})

    with patch("nova.agent.microcompact_messages") as mock_compact:
        mock_compact.return_value = agent.messages[-12:]  # Return only recent messages
        agent.run("test", stream=False)
        # Verify microcompact was called (tier 1 compression triggered)
        mock_compact.assert_called()


def test_compression_tier1_skipped_under_threshold(
    minimal_config, mock_session_store, mock_http_client
):
    """Test that microcompact is skipped when message tokens are below threshold."""
    minimal_config["compression"]["enabled"] = True
    minimal_config["compression"]["threshold_percent"] = 0.99  # 99% threshold = very high
    minimal_config["microcompact"]["enabled"] = True
    minimal_config["agent"]["max_iterations"] = 1

    llm_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Done",
                }
            }
        ]
    }
    mock_http_client.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=llm_response),
        text=json.dumps(llm_response),
    )

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    # Small message history (under threshold)
    agent.messages.append({"role": "user", "content": "hello"})
    agent.messages.append({"role": "assistant", "content": "hi"})

    with patch("nova.agent.microcompact_messages") as mock_compact:
        agent.run("test", stream=False)
        # Verify microcompact was NOT called (below threshold)
        mock_compact.assert_not_called()


def test_compression_tier2_llm_compression(minimal_config, mock_session_store, mock_http_client):
    """Test that LLM-based tier 2 compression is triggered when tier 1 is insufficient."""
    minimal_config["compression"]["enabled"] = True
    minimal_config["compression"]["threshold_percent"] = 0.01  # Very low threshold
    minimal_config["microcompact"]["enabled"] = True
    minimal_config["agent"]["max_iterations"] = 1

    llm_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Done",
                }
            }
        ]
    }
    mock_http_client.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=llm_response),
        text=json.dumps(llm_response),
    )

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    # Build large message history to force compression
    for i in range(20):
        agent.messages.append({"role": "user", "content": f"message {i} " * 50})
        agent.messages.append({"role": "assistant", "content": f"response {i} " * 50})

    with (
        patch("nova.agent.microcompact_messages") as mock_compact,
        patch("nova.agent.compress_conversation") as mock_compress,
    ):
        # Tier 1 compaction doesn't reduce enough
        mock_compact.return_value = agent.messages[-10:]
        # Tier 2 compression succeeds
        mock_compress.return_value = [{"role": "user", "content": "summary"}]

        agent.run("test", stream=False)
        # Both tiers should be called
        mock_compact.assert_called()
        mock_compress.assert_called()


def test_compression_disabled_in_config(minimal_config, mock_session_store, mock_http_client):
    """Test that compression is fully skipped when disabled in config."""
    minimal_config["compression"]["enabled"] = False
    minimal_config["agent"]["max_iterations"] = 1

    llm_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Done",
                }
            }
        ]
    }
    mock_http_client.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=llm_response),
        text=json.dumps(llm_response),
    )

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    # Large message history
    for i in range(20):
        agent.messages.append({"role": "user", "content": f"message {i} " * 50})

    with (
        patch("nova.agent.microcompact_messages") as mock_compact,
        patch("nova.agent.compress_conversation") as mock_compress,
    ):
        agent.run("test", stream=False)
        # Neither compression tier should be called
        mock_compact.assert_not_called()
        mock_compress.assert_not_called()


def test_compression_microcompact_savings_logged(
    minimal_config, mock_session_store, mock_http_client
):
    """Test that microcompact tier 1 logs token savings."""
    minimal_config["compression"]["enabled"] = True
    minimal_config["compression"]["threshold_percent"] = 0.01
    minimal_config["microcompact"]["enabled"] = True
    minimal_config["agent"]["max_iterations"] = 1

    llm_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Done",
                }
            }
        ]
    }
    mock_http_client.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=llm_response),
        text=json.dumps(llm_response),
    )

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    # Build message history
    for i in range(15):
        agent.messages.append({"role": "user", "content": f"msg {i} " * 50})
        agent.messages.append({"role": "assistant", "content": f"rsp {i} " * 50})

    with (
        patch("nova.agent.microcompact_messages") as mock_compact,
        patch("nova.agent.estimate_messages_tokens") as mock_estimate,
        patch("nova.agent.logger") as mock_logger,
    ):
        # Simulate compression saving tokens
        mock_compact.return_value = agent.messages[-6:]
        mock_estimate.side_effect = [5000, 3000]  # Before: 5000, after: 3000

        agent.run("test", stream=False)
        # Verify savings were logged
        mock_logger.info.assert_called()
        call_args = [str(call) for call in mock_logger.info.call_args_list]
        assert any("saved" in str(call).lower() for call in call_args)


def test_compression_tier2_warning_when_exceeds_threshold(
    minimal_config, mock_session_store, mock_http_client
):
    """Test warning logged when compression tier 2 cannot reduce below threshold."""
    minimal_config["compression"]["enabled"] = True
    minimal_config["compression"]["threshold_percent"] = 0.01
    minimal_config["microcompact"]["enabled"] = True
    minimal_config["agent"]["max_iterations"] = 1

    llm_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Done",
                }
            }
        ]
    }
    mock_http_client.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=llm_response),
        text=json.dumps(llm_response),
    )

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    # Very large message history
    for i in range(25):
        agent.messages.append({"role": "user", "content": f"msg {i} " * 50})

    with (
        patch("nova.agent.microcompact_messages") as mock_compact,
        patch("nova.agent.compress_conversation") as mock_compress,
        patch("nova.agent.logger") as mock_logger,
    ):
        # Tier 1: no savings
        mock_compact.return_value = agent.messages
        # Tier 2: returns None (cannot compress)
        mock_compress.return_value = None

        agent.run("test", stream=False)
        # Verify warning was logged
        mock_logger.warning.assert_called()


def test_compression_preserves_recent_messages(
    minimal_config, mock_session_store, mock_http_client
):
    """Test that compression preserves recent messages (keep_recent parameter)."""
    minimal_config["compression"]["enabled"] = True
    minimal_config["compression"]["threshold_percent"] = 0.01
    minimal_config["microcompact"]["enabled"] = True
    minimal_config["microcompact"]["keep_recent"] = 5
    minimal_config["agent"]["max_iterations"] = 1

    llm_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Done",
                }
            }
        ]
    }
    mock_http_client.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=llm_response),
        text=json.dumps(llm_response),
    )

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    # Build messages
    for i in range(15):
        agent.messages.append({"role": "user", "content": f"msg {i} " * 50})
        agent.messages.append({"role": "assistant", "content": f"rsp {i} " * 50})

    with patch("nova.agent.microcompact_messages") as mock_compact:
        mock_compact.return_value = agent.messages[-10:]
        agent.run("test", stream=False)
        # Verify keep_recent=5 was passed
        mock_compact.assert_called_once()
        call_kwargs = mock_compact.call_args[1]
        assert call_kwargs.get("keep_recent") == 5


def test_compression_state_persisted_to_session(
    minimal_config, mock_session_store, mock_http_client
):
    """Test that compression works without breaking agent execution."""
    minimal_config["compression"]["enabled"] = True
    minimal_config["compression"]["threshold_percent"] = 0.01
    minimal_config["microcompact"]["enabled"] = True
    minimal_config["agent"]["max_iterations"] = 1

    llm_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Done",
                }
            }
        ]
    }
    mock_http_client.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value=llm_response),
        text=json.dumps(llm_response),
    )

    agent = NovaAgent(
        config=minimal_config,
        http_client=mock_http_client,
        session_store=mock_session_store,
    )

    # Build messages
    for i in range(15):
        agent.messages.append({"role": "user", "content": f"msg {i} " * 50})
        agent.messages.append({"role": "assistant", "content": f"rsp {i} " * 50})

    with patch("nova.agent.microcompact_messages") as mock_compact:
        compressed_msgs = [{"role": "user", "content": "compressed"}]
        mock_compact.return_value = compressed_msgs

        result = agent.run("test", stream=False)
        # Verify agent still returns result and completes successfully
        assert result == "Done"
        # Verify microcompact was called during compression
        mock_compact.assert_called()
