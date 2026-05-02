"""CLI entry point for Nova Agent."""

import argparse
import sys
from pathlib import Path

from nova.agent import NovaAgent
from nova.config import load_config


def cmd_chat(args):
    """Start an interactive chat session."""
    config = load_config()
    agent = NovaAgent(config=config, session_id=args.session)
    agent.chat_loop()


def cmd_ask(args):
    """Ask a one-shot question."""
    config = load_config()
    agent = NovaAgent(config=config)
    response = agent.run(args.question, stream=False)
    print(response)


def cmd_sessions(args):
    """List recent sessions."""
    config = load_config()
    from nova.session import SessionStore

    session_dir = Path(config["session"]["directory"]).expanduser()
    store = SessionStore(session_dir / "sessions.db")

    sessions = store.list_sessions(limit=args.limit)
    if not sessions:
        print("No sessions found.")
        return

    print(f"{'Session ID':<30} {'Title':<25} {'Messages':<10} {'Updated':<25}")
    print("-" * 90)
    for s in sessions:
        title = (s.get("title") or "(untitled)")[:23]
        updated = (s.get("updated_at") or "")[:19]
        print(f"{s['session_id']:<30} {title:<25} {s['message_count']:<10} {updated:<25}")


def cmd_reset(args):
    """Reset (clear) the current session."""
    if args.session_id:
        print(f"Session deletion not yet implemented for {args.session_id}")
    else:
        print("Use 'nova sessions' to see sessions, then 'nova reset --session <id>'")


def main():
    parser = argparse.ArgumentParser(
        prog="nova",
        description="Nova Agent — A minimalist personal AI assistant",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # chat
    chat_parser = subparsers.add_parser("chat", help="Start an interactive chat session")
    chat_parser.add_argument("--session", help="Resume a specific session ID")
    chat_parser.set_defaults(func=cmd_chat)

    # ask
    ask_parser = subparsers.add_parser("ask", help="Ask a one-shot question")
    ask_parser.add_argument("question", help="The question to ask")
    ask_parser.set_defaults(func=cmd_ask)

    # sessions
    sessions_parser = subparsers.add_parser("sessions", help="List recent sessions")
    sessions_parser.add_argument("--limit", type=int, default=20, help="Max sessions to show")
    sessions_parser.set_defaults(func=cmd_sessions)

    # reset
    reset_parser = subparsers.add_parser("reset", help="Reset session")
    reset_parser.add_argument("--session", dest="session_id", help="Session ID to reset")
    reset_parser.set_defaults(func=cmd_reset)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
