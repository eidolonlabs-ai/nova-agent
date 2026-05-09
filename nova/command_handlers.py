"""Slash command handler registry.

Provides a decorator-based pattern for registering slash command handlers.
Handlers are extracted from the agent's chat_loop into this module for
clean separation of concerns.

Usage:
    @command_handler("status", aliases=("st",))
    def cmd_status(agent: NovaAgent, args: str) -> None:
        ...
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nova.agent import NovaAgent

logger = logging.getLogger(__name__)

# Type alias for command handlers
CommandHandler = Callable[["NovaAgent", str], None]

# Registry: canonical name -> handler function
_HANDLERS: dict[str, CommandHandler] = {}


def command_handler(
    name: str, aliases: tuple[str, ...] = ()
) -> Callable[[CommandHandler], CommandHandler]:
    """Decorator to register a slash command handler.

    Args:
        name: Canonical command name (without leading /).
        aliases: Tuple of alternative names.

    Example:
        @command_handler("status", aliases=("st",))
        def cmd_status(agent: NovaAgent, args: str) -> None:
            ...
    """

    def decorator(func: CommandHandler) -> CommandHandler:
        _HANDLERS[name] = func
        for alias in aliases:
            _HANDLERS[alias] = func
        logger.debug("Registered command handler: %s (aliases: %s)", name, aliases)
        return func

    return decorator


def dispatch_command(name: str, agent: NovaAgent, args: str) -> bool:
    """Dispatch a slash command to its registered handler.

    Args:
        name: Command name (without leading /).
        agent: The NovaAgent instance.
        args: Raw argument string after the command name.

    Returns:
        True if a handler was found and executed, False otherwise.
    """
    handler = _HANDLERS.get(name.lower())
    if handler is None:
        skill_match = _resolve_skill(name, agent.config)
        if skill_match is not None:
            _handle_skill(agent, skill_match)
            return True
        return False
    try:
        handler(agent, args)
        return True
    except Exception as e:
        logger.error("Command '%s' failed: %s", name, e)
        from nova.display import _DIM, _RST, _cprint

        _cprint(f"{_DIM}Command error: {e}{_RST}")
        return True


def get_registered_commands() -> set[str]:
    """Return the set of canonical command names (excludes aliases)."""
    # Import here to avoid circular dependency
    from nova.commands import COMMAND_REGISTRY

    return {cmd.name for cmd in COMMAND_REGISTRY}


def get_skill_names(config: dict) -> set[str]:
    """Get all available skill names from the configured skills directory."""
    from pathlib import Path

    from nova.skills import discover_skills

    skills_dir = Path(config.get("skills", {}).get("directory", "~/.nova/skills")).expanduser()
    skills = discover_skills(skills_dir)
    return {skill["name"] for skill in skills}


def _resolve_skill(name: str, config: dict) -> str | None:
    """Match a slash-command name to a skill, case-insensitive. Returns the canonical name."""
    target = name.lower()
    for skill_name in get_skill_names(config):
        if skill_name.lower() == target:
            return skill_name
    return None


# ─── Built-in command handlers ───────────────────────────────────────────────


@command_handler("new", aliases=("reset",))
def cmd_new(agent: NovaAgent, args: str) -> None:
    from nova.display import _DIM, _RST, _cprint

    agent._create_session()
    _cprint(f"{_DIM}New session started{_RST}")


@command_handler("history")
def cmd_history(agent: NovaAgent, args: str) -> None:
    from nova.display import _CYAN, _RST, _cprint

    for msg in agent.messages:
        role = msg.get("role", "")
        content = msg.get("content") or ""
        if role == "user":
            _cprint(f"\n{_CYAN}❯ {content}{_RST}")
        elif role == "assistant" and content:
            preview = content[:200] + "…" if len(content) > 200 else content
            _cprint(f"  {preview}")


@command_handler("status", aliases=("st",))
def cmd_status(agent: NovaAgent, args: str) -> None:
    from nova.display import _DIM, _RST, _cprint
    from nova.tokens import estimate_total_request_tokens

    ctx = estimate_total_request_tokens(
        agent.messages,
        system_prompt=agent._cached_system_prompt or "",
    )
    _cprint(f"{_DIM}Session: {agent.session_id}")
    _cprint(f"Model:   {agent.config['openrouter']['model']}")
    _cprint(f"Context: {ctx:,} tokens")
    # Delegation state
    delegation_cfg = agent.config.get("delegation", {})
    if delegation_cfg.get("enabled"):
        max_depth = delegation_cfg.get("max_spawn_depth", 2)
        role = "leaf" if agent.is_leaf_agent else "orchestrator"
        _cprint(f"Delegation: enabled  depth={agent.depth}/{max_depth}  role={role}")
    else:
        _cprint("Delegation: disabled")
    _cprint(f"Messages: {len(agent.messages)}{_RST}")


@command_handler("sessions")
def cmd_sessions(agent: NovaAgent, args: str) -> None:
    from nova.display import _DIM, _RST, _cprint

    sessions = agent.session_store.list_sessions(limit=10)
    if not sessions:
        _cprint(f"{_DIM}No sessions found{_RST}")
    for s in sessions:
        _cprint(f"{_DIM}{s.get('id', '')}  {s.get('created_at', '')}{_RST}")


@command_handler("model")
def cmd_model(agent: NovaAgent, args: str) -> None:
    from nova.display import _DIM, _RST, _cprint

    if args:
        agent.config["openrouter"]["model"] = args.strip()
        _cprint(f"{_DIM}Model switched to: {args.strip()}{_RST}")
    else:
        _cprint(f"{_DIM}Current model: {agent.config['openrouter']['model']}{_RST}")


@command_handler("tools")
def cmd_tools(agent: NovaAgent, args: str) -> None:
    from nova.display import _CYAN, _DIM, _RST, _cprint
    from nova.tools.registry import registry

    tools = registry.get_definitions()
    _cprint(f"{_DIM}Available tools ({len(tools)}):{_RST}")
    for t in tools:
        _cprint(
            f"  {_CYAN}{t['function']['name']}{_RST}{_DIM}  —  {t['function'].get('description', '')[:60]}{_RST}"
        )


@command_handler("skills")
def cmd_skills(agent: NovaAgent, args: str) -> None:
    from pathlib import Path

    from nova.display import _CYAN, _DIM, _RST, _cprint
    from nova.skills import discover_skills

    skills_dir = Path(
        agent.config.get("skills", {}).get("directory", "~/.nova/skills")
    ).expanduser()
    skills = discover_skills(skills_dir)

    if not skills:
        _cprint(f"{_DIM}No skills found. Create skills in ~/.nova/skills/.{_RST}")
        return

    _cprint(f"{_DIM}Available skills ({len(skills)}):{_RST}")

    by_category: dict[str, list[dict]] = {}
    for skill in skills:
        by_category.setdefault(skill["category"], []).append(skill)

    for category in sorted(by_category.keys()):
        _cprint(f"{_CYAN}{category}{_RST}")
        for skill in by_category[category]:
            desc = skill["description"]
            if len(desc) > 60:
                desc = desc[:60] + "…"
            _cprint(f"  {_DIM}/{skill['name']:<20} — {desc}{_RST}")


@command_handler("usage")
def cmd_usage(agent: NovaAgent, args: str) -> None:
    from nova.display import _DIM, _RST, _cprint
    from nova.model_metadata import get_model_context_window
    from nova.tokens import estimate_total_request_tokens

    ctx = estimate_total_request_tokens(
        agent.messages,
        system_prompt=agent._cached_system_prompt or "",
    )
    cw = get_model_context_window(agent.config["openrouter"]["model"])
    pct = int(ctx / cw * 100) if cw else 0
    _cprint(f"{_DIM}Context used: {ctx:,} / {cw:,} tokens ({pct}%){_RST}")
    if agent.cost_tracker:
        _cprint(f"{_DIM}{agent.cost_tracker.format_summary()}{_RST}")


@command_handler("undo")
def cmd_undo(agent: NovaAgent, args: str) -> None:
    from nova.display import _DIM, _RST, _cprint

    # Remove last user+assistant pair
    if len(agent.messages) >= 2:
        agent.messages = agent.messages[:-2]
        _cprint(f"{_DIM}Last exchange removed{_RST}")
    else:
        _cprint(f"{_DIM}Nothing to undo{_RST}")


@command_handler("compact")
def cmd_compact(agent: NovaAgent, args: str) -> None:
    from nova.display import _DIM, _RST, _cprint

    _cprint(f"{_DIM}Compacting context…{_RST}")
    # Keep system prompt + last 4 messages
    if len(agent.messages) > 4:
        agent.messages = agent.messages[-4:]
    _cprint(f"{_DIM}Context compacted to {len(agent.messages)} messages{_RST}")


@command_handler("copy")
def cmd_copy(agent: NovaAgent, args: str) -> None:
    import subprocess

    from nova.display import _DIM, _RST, _cprint

    # Find last assistant message
    for msg in reversed(agent.messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            subprocess.run(
                ["pbcopy"],
                input=msg["content"].encode(),
                check=False,
            )
            _cprint(f"{_DIM}Copied to clipboard{_RST}")
            return
    _cprint(f"{_DIM}No response to copy{_RST}")


@command_handler("memory")
def cmd_memory(agent: NovaAgent, args: str) -> None:
    from nova.display import _DIM, _RST, _cprint

    sub = args.split(None, 1)[0].lower() if args else "list"
    query = args.split(None, 1)[1] if len(args.split(None, 1)) > 1 else ""
    if not agent.memory:
        _cprint(f"{_DIM}Memory is disabled{_RST}")
        return
    if sub == "clear":
        agent.memory.clear()
        _cprint(f"{_DIM}Memory cleared{_RST}")
    elif sub == "search" and query:
        results = agent.memory.search(query)
        for r in results:
            _cprint(f"  {_DIM}{r}{_RST}")
    else:
        entries = agent.memory.get_all()
        if not entries:
            _cprint(f"{_DIM}No memories stored{_RST}")
        for e in entries:
            _cprint(f"  {_DIM}{e}{_RST}")


def _handle_skill(agent: NovaAgent, skill_name: str) -> None:
    """Load and display a skill via slash command."""
    from pathlib import Path

    from nova.display import _CYAN, _DIM, _RST, _cprint
    from nova.skills import load_skill_content

    skills_dir = Path(
        agent.config.get("skills", {}).get("directory", "~/.nova/skills")
    ).expanduser()
    skill_dir_path = skills_dir / skill_name
    skill_path = skill_dir_path / "SKILL.md"

    content = load_skill_content(str(skill_path), skill_dir=skill_dir_path)
    if content is None:
        _cprint(f"{_DIM}Error: Skill '{skill_name}' not found.{_RST}")
        return

    divider = "─" * 60
    _cprint(f"\n{_CYAN}{divider}")
    _cprint(f"Skill: {skill_name}")
    _cprint(f"{divider}{_RST}\n")
    _cprint(content)
    _cprint(f"\n{_CYAN}{divider}{_RST}\n")
