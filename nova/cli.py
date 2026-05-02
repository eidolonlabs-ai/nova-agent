"""CLI entry point for Nova Agent."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from nova.agent import NovaAgent
from nova.config import ensure_nova_home, load_config


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


def cmd_setup(args):
    """Interactive setup wizard to configure Nova Agent."""
    import yaml

    nova_home = ensure_nova_home()
    config_path = nova_home / "config.yaml"

    print("╔══════════════════════════════════════════════════════╗")
    print("║           ✦ Nova Agent Setup Wizard                  ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # Load existing config if present
    existing_config = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            existing_config = yaml.safe_load(f) or {}

    # Get OpenRouter API key
    current_key = existing_config.get("openrouter", {}).get("api_key", "")
    env_key = os.environ.get("OPENROUTER_API_KEY", "")

    if env_key:
        print("✓ OPENROUTER_API_KEY found in environment")
        api_key = env_key
    elif current_key:
        masked = current_key[:8] + "..." if len(current_key) > 8 else current_key
        print(f"✓ API key already configured: {masked}")
        api_key = current_key
    else:
        print("OpenRouter API key is required.")
        print("Get one at: https://openrouter.ai/keys")
        print()
        api_key = input("Enter your OpenRouter API key: ").strip()
        if not api_key:
            print("✗ API key is required. Setup cancelled.")
            sys.exit(1)

    # Get model preference
    current_model = existing_config.get("openrouter", {}).get("model", "")
    if current_model:
        print(f"\nCurrent model: {current_model}")
        change = input("Change model? [y/N]: ").strip().lower()
        if change in ("y", "yes"):
            model = input("Enter model (e.g. anthropic/claude-sonnet-4-20250514): ").strip()
        else:
            model = current_model
    else:
        print("\nSelect a model:")
        print("  1. anthropic/claude-sonnet-4-20250514 (recommended)")
        print("  2. anthropic/claude-opus-4-20250514")
        print("  3. google/gemini-2.5-pro")
        print("  4. openai/gpt-4.1")
        print("  5. Custom model")
        choice = input("\nChoice [1]: ").strip() or "1"
        models = {
            "1": "anthropic/claude-sonnet-4-20250514",
            "2": "anthropic/claude-opus-4-20250514",
            "3": "google/gemini-2.5-pro",
            "4": "openai/gpt-4.1",
        }
        if choice == "5":
            model = input("Enter model name: ").strip()
        else:
            model = models.get(choice, models["1"])

    # Build config
    config = existing_config
    config.setdefault("openrouter", {})
    config["openrouter"]["api_key"] = api_key
    config["openrouter"]["model"] = model

    # Write config
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"\n✓ Configuration saved to {config_path}")
    print()
    print("Setup complete! Run 'nova chat' to start.")


def cmd_update(args):
    """Update Nova Agent to the latest version."""
    # Find the install directory (parent of the nova package)
    nova_package_dir = Path(__file__).parent.parent
    install_dir = nova_package_dir

    if not (install_dir / ".git").exists():
        print("✗ Could not find git repository. Nova may have been installed via pip.")
        print("  To update, run: pip install --upgrade nova-agent")
        sys.exit(1)

    print("Updating Nova Agent...")
    print(f"  Repository: {install_dir}")

    # Check for uncommitted changes
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=install_dir,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        print(" Uncommitted changes detected. Stashing before update...")
        subprocess.run(["git", "stash", "push", "--include-untracked"], cwd=install_dir, check=True)

    # Fetch and pull
    subprocess.run(["git", "fetch", "origin"], cwd=install_dir, check=True)
    result = subprocess.run(
        ["git", "pull", "--ff-only", "origin", "main"],
        cwd=install_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"✗ Pull failed: {result.stderr}")
        print("  You may have local changes. Run 'git pull' manually.")
        sys.exit(1)

    # Reinstall dependencies
    venv_python = install_dir / "venv" / "bin" / "python"
    if venv_python.exists():
        print("Reinstalling dependencies...")
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-e", ".[dev]"],
            cwd=install_dir,
            check=True,
        )
    else:
        print("⚠ No virtual environment found. Run 'pip install -e .' manually.")

    print("\n✓ Nova Agent updated successfully!")
    print("  Run 'nova chat' to start.")


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

    # setup
    setup_parser = subparsers.add_parser("setup", help="Interactive setup wizard")
    setup_parser.set_defaults(func=cmd_setup)

    # update
    update_parser = subparsers.add_parser("update", help="Update Nova Agent to latest version")
    update_parser.set_defaults(func=cmd_update)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
