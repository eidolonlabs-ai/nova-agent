"""Tests for CLI argument parsing."""

import sys
from unittest.mock import patch

from nova.cli import main


def test_cli_no_args_prints_help(capsys):
    """Test that running with no args prints help and exits."""
    with patch.object(sys, "argv", ["nova"]):
        try:
            main()
        except SystemExit as e:
            assert e.code == 1

    captured = capsys.readouterr()
    assert "usage" in captured.out.lower() or "nova" in captured.out.lower()


def test_cli_chat_command_parsing():
    """Test that 'chat' command is parsed correctly."""
    with patch("nova.cli.cmd_chat") as mock_chat:
        with patch.object(sys, "argv", ["nova", "chat"]):
            main()
        mock_chat.assert_called_once()


def test_cli_chat_with_session():
    """Test that 'chat --session <id>' passes session arg."""
    with patch("nova.cli.cmd_chat") as mock_chat:
        with patch.object(sys, "argv", ["nova", "chat", "--session", "abc123"]):
            main()
        args = mock_chat.call_args[0][0]
        assert args.session == "abc123"


def test_cli_ask_command_parsing():
    """Test that 'ask' command is parsed correctly."""
    with patch("nova.cli.cmd_ask") as mock_ask:
        with patch.object(sys, "argv", ["nova", "ask", "what is python?"]):
            main()
        args = mock_ask.call_args[0][0]
        assert args.question == "what is python?"


def test_cli_sessions_command_parsing():
    """Test that 'sessions' command is parsed correctly."""
    with patch("nova.cli.cmd_sessions") as mock_sessions:
        with patch.object(sys, "argv", ["nova", "sessions"]):
            main()
        args = mock_sessions.call_args[0][0]
        assert args.limit == 20  # default


def test_cli_sessions_with_limit():
    """Test that 'sessions --limit 5' passes limit arg."""
    with patch("nova.cli.cmd_sessions") as mock_sessions:
        with patch.object(sys, "argv", ["nova", "sessions", "--limit", "5"]):
            main()
        args = mock_sessions.call_args[0][0]
        assert args.limit == 5


def test_cli_reset_command_parsing():
    """Test that 'reset' command is parsed correctly."""
    with patch("nova.cli.cmd_reset") as mock_reset:
        with patch.object(sys, "argv", ["nova", "reset"]):
            main()
        mock_reset.assert_called_once()


def test_cli_reset_with_session():
    """Test that 'reset --session <id>' passes session_id arg."""
    with patch("nova.cli.cmd_reset") as mock_reset:
        with patch.object(sys, "argv", ["nova", "reset", "--session", "xyz789"]):
            main()
        args = mock_reset.call_args[0][0]
        assert args.session_id == "xyz789"
