"""Slash command registry and autocomplete for Nova CLI.

Single source of truth for all slash commands. Autocomplete, help text,
and dispatch all derive from COMMAND_REGISTRY.
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.document import Document
except ImportError:  # pragma: no cover
    Completer = object    # type: ignore[assignment,misc,misc]
    Completion = None   # type: ignore[assignment,misc]
    Document = None     # type: ignore[assignment,misc]


@dataclass(frozen=True)
class CommandDef:
    name: str                          # canonical name without slash
    description: str
    category: str
    aliases: tuple[str, ...] = ()
    args_hint: str = ""
    subcommands: tuple[str, ...] = ()


COMMAND_REGISTRY: list[CommandDef] = [
    # Session
    CommandDef("new",      "Start a fresh session",                    "Session", aliases=("reset",)),
    CommandDef("clear",    "Clear screen",                             "Session"),
    CommandDef("history",  "Show conversation history",                "Session"),
    CommandDef("undo",     "Remove the last exchange",                 "Session"),
    CommandDef("retry",    "Resend the last message",                  "Session"),
    CommandDef("status",   "Show session info",                        "Session"),
    CommandDef("sessions", "List recent sessions",                     "Session"),
    CommandDef("resume",   "Resume a previous session",                "Session", args_hint="[id]"),
    CommandDef("title",    "Set a title for this session",             "Session", args_hint="[name]"),
    CommandDef("compact",  "Summarise and compress context",           "Session"),

    # Configuration
    CommandDef("model",    "Show or switch model",                     "Configuration", args_hint="[model]"),
    CommandDef("config",   "Show current configuration",               "Configuration"),
    CommandDef("reasoning","Toggle reasoning display",                 "Configuration",
               subcommands=("show", "hide"), args_hint="[show|hide]"),

    # Memory
    CommandDef("memory",   "Search or clear memory",                   "Memory",
               subcommands=("search", "clear", "list"), args_hint="[search|clear|list] [query]"),

    # Skills
    CommandDef("skills",   "List or manage skills",                    "Skills",
               subcommands=("list", "view"), args_hint="[list|view] [name]"),

    # Tools
    CommandDef("tools",    "List available tools",                     "Tools"),

    # Info
    CommandDef("help",     "Show available commands",                  "Info"),
    CommandDef("copy",     "Copy last response to clipboard",          "Info"),
    CommandDef("usage",    "Show token usage for this session",        "Info"),

    # Exit
    CommandDef("quit",     "Exit Nova",                                "Exit", aliases=("exit", "q")),
]


def _build_lookup() -> dict[str, CommandDef]:
    lookup: dict[str, CommandDef] = {}
    for cmd in COMMAND_REGISTRY:
        lookup[cmd.name] = cmd
        for alias in cmd.aliases:
            lookup[alias] = cmd
    return lookup


_LOOKUP: dict[str, CommandDef] = _build_lookup()


def resolve_command(name: str) -> CommandDef | None:
    """Resolve a name (with or without leading /) to its CommandDef."""
    return _LOOKUP.get(name.lower().lstrip("/"))


def get_commands_by_category() -> dict[str, list[CommandDef]]:
    seen: set[str] = set()
    cats: dict[str, list[CommandDef]] = {}
    for cmd in COMMAND_REGISTRY:
        if cmd.name not in seen:
            seen.add(cmd.name)
            cats.setdefault(cmd.category, []).append(cmd)
    return cats


class SlashCompleter(Completer):
    """Tab-completion for slash commands, matching Hermes' SlashCommandCompleter."""

    def get_completions(self, document, complete_event):  # type: ignore[override]
        text = document.text_before_cursor
        if not text.startswith("/"):
            return

        parts = text[1:].split(" ", 1)
        cmd_part = parts[0].lower()
        has_space = len(parts) > 1

        if not has_space:
            # Complete command name
            for cmd in COMMAND_REGISTRY:
                names = [cmd.name] + list(cmd.aliases)
                for name in names:
                    if name.startswith(cmd_part):
                        hint = f" {cmd.args_hint}" if cmd.args_hint else ""
                        display_text = f"/{name}{hint}"
                        yield Completion(
                            name[len(cmd_part):],
                            display=display_text,
                            display_meta=cmd.description,
                        )
        else:
            # Complete subcommand
            resolved = resolve_command(cmd_part)
            if resolved and resolved.subcommands:
                sub_part = parts[1].lower()
                for sub in resolved.subcommands:
                    if sub.startswith(sub_part):
                        yield Completion(
                            sub[len(sub_part):],
                            display=sub,
                        )
