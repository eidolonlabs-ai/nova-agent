"""CLI presentation — banner, spinner, thinking blocks, tool preview formatting.

Pure display functions and classes with no NovaAgent dependency.
"""

import re
import shutil
import sys
import threading
import time
from contextlib import suppress
from typing import Any

from nova import __version__

# ─── ASCII Art Banner ────────────────────────────────────────────────────────

NOVA_BANNER = """\
[bold #00D4FF]  ██  ██  ████  ██  ██  ████  [/]
[#00B4D8]  ███ ██ ██  ██ ██  ██ ██  ██ [/]
[#00B4D8]  ██ ██  ██  ██  ████  ██████ [/]
[#0096C7]  ██  ██ ██  ██   ███  ██  ██ [/]
[#0096C7]  ██  ██  ████     █   ██  ██ [/]"""

NOVA_TAGLINE = "[dim]A minimalist personal AI agent by Eidolon Labs LLC[/dim]"


def print_banner(console, config: dict) -> None:
    """Print the Nova splash banner at chat startup.

    Matches the Hermes-Agent pattern: ASCII art logo + version + model + session.
    """
    from rich.panel import Panel
    from rich.table import Table

    model = config["openrouter"]["model"]
    model_short = model.split("/")[-1] if "/" in model else model

    # Build info table
    info = Table.grid(padding=(0, 2))
    info.add_column(style="cyan", justify="right")
    info.add_column(style="white")
    info.add_row("model", model_short)
    info.add_row("version", f"v{__version__}")

    # Build the banner panel
    banner_content = f"{NOVA_BANNER}\n\n{NOVA_TAGLINE}"

    console.print(
        Panel(
            banner_content,
            border_style="#00D4FF",
            padding=(1, 2),
        )
    )

    # Info line below banner
    console.print()
    console.print(info)
    console.print()
    console.print("[dim]Type [bold]quit[/bold] to exit, [bold]new[/bold] for new session[/dim]")
    console.print()


# ─── Reasoning/Thinking Block Handling ───────────────────────────────────────

# Reasoning/thinking tag variants used by different models
_REASONING_TAGS = (
    "think",
    "thinking",
    "reasoning",
    "thought",
)


def strip_reasoning_tags(text: str) -> str:
    """Remove reasoning/thinking blocks from displayed text.

    Handles closed pairs, unterminated open tags, and orphan close tags.
    """
    cleaned = text
    for tag in sorted(_REASONING_TAGS, key=len, reverse=True):
        # Closed pair
        cleaned = re.sub(
            rf"<{tag}>.*?</{tag}>\s*",
            "",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Unterminated open tag
        cleaned = re.sub(
            rf"<{tag}>.*$",
            "",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Orphan close tag
        cleaned = re.sub(
            rf"</{tag}>\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
    return cleaned.strip()


def extract_reasoning_blocks(text: str) -> list[dict[str, str | int]]:
    """Extract reasoning/thinking blocks from text.

    Returns list of dicts with 'tag', 'content', and 'start'/'end' positions.
    """
    blocks: list[dict[str, str | int]] = []
    for tag in sorted(_REASONING_TAGS, key=len, reverse=True):
        for match in re.finditer(
            rf"<{tag}>(.*?)</{tag}>",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        ):
            blocks.append({
                "tag": tag,
                "content": match.group(1).strip(),
                "start": match.start(),
                "end": match.end(),
            })
    # Sort by position
    blocks.sort(key=lambda b: b["start"])  # type: ignore[arg-type]
    return blocks


def split_reasoning_and_response(text: str) -> tuple[list[dict[str, str | int]], str]:
    """Split text into reasoning blocks and final response.

    Returns (reasoning_blocks, response_text).
    """
    blocks = extract_reasoning_blocks(text)
    if not blocks:
        return [], text

    # Build response by removing reasoning blocks
    response = text
    for block in reversed(blocks):
        start = block["start"]
        end = block["end"]
        if isinstance(start, int) and isinstance(end, int):
            response = response[:start] + response[end:]

    return blocks, response.strip()


# ─── Footer spinner (Hermes-style status bar) ────────────────────────────────

_SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

KAWAII_FACES = [
    "(｡◕‿◕｡)", "( ˘▽˘)っ", "(◕ᴗ◕)", "(✿◠◠)", "٩(◕‿◕｡)۶",
    "ヾ(＾∇＾)", "(≧◡≦)", "♪(´ε` )", "(★ω★)", "ヽ(>∀<☆)☆",
    "(´·_·`)", "(¬‿¬)", "( •_•)>⌐■-■", "(⌐■_■)", "٩(๑❛ᴗ❛๑)۶",
]

THINKING_VERBS = [
    "pondering", "contemplating", "musing", "cogitating", "ruminating",
    "deliberating", "mulling", "reflecting", "processing", "reasoning",
    "analyzing", "computing", "synthesizing", "formulating",
]


class NovaTUI:
    """prompt_toolkit Application-based TUI.

    Architecture mirrors Hermes-Agent:
    - A full pt Application owns the screen (status bar + input area as layout widgets).
    - The agent runs in a daemon thread, communicating via a queue.Queue.
    - All output goes through patch_stdout → StdoutProxy → injected above the TUI chrome.
    - A separate spinner thread calls app.invalidate() at 100ms intervals so the
      status bar animates while the agent is running.
    - The event loop (main thread) is never blocked, so StdoutProxy flushes immediately.
    """

    def __init__(self, model: str, context_window: int = 0):
        self.model_short = model.split("/")[-1] if "/" in model else model
        self.context_window = context_window
        self.context_tokens = 0
        self.session_start = time.monotonic()
        self._agent_running = threading.Event()   # thread-safe flag
        self._interrupt_requested = threading.Event()  # Ctrl+C → cancel agent
        self._last_ctrl_c_time: float = 0.0           # for double Ctrl+C force-exit
        self._spinner_frame = 0
        self._spinner_verb_idx = 0
        self._app: Any | None = None          # prompt_toolkit Application
        self._should_exit = threading.Event()  # thread-safe exit flag
        self._last_invalidate: float = 0.0    # throttle repaint calls

    # ── Status bar fragments (called on every repaint) ────────────────────────

    def _status_bar_fragments(self) -> list:
        elapsed = time.monotonic() - self.session_start
        e = int(elapsed)
        elapsed_str = f"{e // 60}m {e % 60}s" if e >= 60 else f"{e}s"

        if self._interrupt_requested.is_set():
            label = "interrupting…"
        elif self._agent_running.is_set():
            frame = _SPINNER_FRAMES[self._spinner_frame % len(_SPINNER_FRAMES)]
            verb = THINKING_VERBS[self._spinner_verb_idx % len(THINKING_VERBS)]
            label = f"{frame} {verb}…  ^C to stop"
        else:
            label = "ready"

        frags = [
            ("class:status-bar", " – "),
            ("class:status-bar-strong", label),
            ("class:status-bar-dim", " │ "),
            ("class:status-bar-dim", self.model_short),
        ]

        if self.context_window > 0:
            pct = int((self.context_tokens / self.context_window) * 100)
            bar_w = 14
            filled = round((pct / 100) * bar_w)
            bar = "█" * filled + "░" * (bar_w - filled)

            def _fmt(n: int) -> str:
                return f"{n / 1000:.1f}k" if n >= 1000 else str(n)

            bar_style = (
                "class:status-bar-critical" if pct >= 90
                else "class:status-bar-warn" if pct >= 70
                else "class:status-bar-good"
            )
            frags += [
                ("class:status-bar-dim", " │ "),
                ("class:status-bar-dim", f"{_fmt(self.context_tokens)}/{_fmt(self.context_window)}"),
                ("class:status-bar-dim", " │ "),
                (bar_style, f"[{bar}]"),
                ("class:status-bar-dim", f" {pct}%"),
            ]

        frags += [
            ("class:status-bar-dim", " │ "),
            ("class:status-bar-dim", elapsed_str),
            ("class:status-bar", " "),
        ]
        return frags

    def _invalidate(self, min_interval: float = 0.1) -> None:
        """Throttled repaint — prevents terminal blinking on slow/SSH connections."""
        now = time.monotonic()
        if now - self._last_invalidate < min_interval:
            return
        self._last_invalidate = now
        if self._app is not None:
            with suppress(Exception):
                self._app.invalidate()

    # ── Main run loop ─────────────────────────────────────────────────────────

    def run(self, on_input):
        """Run the TUI. Calls on_input(text) for each user message."""
        import os
        import queue

        from prompt_toolkit import Application
        from prompt_toolkit.filters import Condition
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import Layout
        from prompt_toolkit.layout.containers import HSplit, Window
        from prompt_toolkit.layout.controls import FormattedTextControl
        from prompt_toolkit.layout.dimension import Dimension
        from prompt_toolkit.layout.menus import CompletionsMenu
        from prompt_toolkit.patch_stdout import patch_stdout
        from prompt_toolkit.styles import Style
        from prompt_toolkit.widgets import TextArea

        from nova.commands import SlashCompleter, get_commands_by_category, resolve_command

        style = Style.from_dict({
            "prompt":               "#00D4FF bold",
            "input-area":          "#ffffff",
            "status-bar":          "bg:#1a1a2e #888888",
            "status-bar-strong":   "bg:#1a1a2e #00D4FF bold",
            "status-bar-dim":      "bg:#1a1a2e #555555",
            "status-bar-good":     "bg:#1a1a2e #00AA00 bold",
            "status-bar-warn":     "bg:#1a1a2e #FFD700 bold",
            "status-bar-critical": "bg:#1a1a2e #FF4444 bold",
        })

        # ── Input queue (agent thread reads from this) ────────────────────────
        _input_queue: queue.Queue[str] = queue.Queue()

        # Expose interrupt event to agent so it can check mid-iteration
        self._interrupt_requested.clear()

        # ── Input area (TextArea — handles history, completion, prompt) ───────
        history_path = os.path.expanduser("~/.nova/history")
        os.makedirs(os.path.dirname(history_path), exist_ok=True)

        input_area = TextArea(
            height=Dimension(min=1, max=5, preferred=1),
            prompt=[("class:prompt", "❯ ")],
            style="class:input-area",
            multiline=False,
            wrap_lines=True,
            read_only=Condition(lambda: self._agent_running.is_set()),
            history=FileHistory(history_path),
            completer=SlashCompleter(),
            complete_while_typing=True,
        )

        # ── Key bindings ──────────────────────────────────────────────────────
        kb = KeyBindings()

        @kb.add("enter")
        def _handle_enter(event):
            text = input_area.text.strip()
            if text and not self._agent_running.is_set():
                event.app.current_buffer.reset(append_to_history=True)
                _input_queue.put(text)

        @kb.add("escape", "enter")
        @kb.add("c-j")
        def _handle_newline(event):
            """Alt+Enter / Ctrl+J inserts a newline for multi-line input."""
            event.current_buffer.insert_text("\n")

        @kb.add("c-c")
        def _handle_ctrl_c(event):
            now = time.monotonic()
            if self._agent_running.is_set():
                if now - self._last_ctrl_c_time < 2.0:
                    # Second Ctrl+C within 2s → force exit
                    _cprint(f"{_DIM}Force exiting…{_RST}")
                    self._should_exit.set()
                    event.app.exit()
                else:
                    # First Ctrl+C → signal interrupt
                    self._last_ctrl_c_time = now
                    self._interrupt_requested.set()
                    _cprint(f"{_DIM}Interrupting… (Ctrl+C again to force exit){_RST}")
            else:
                if event.app.current_buffer.text:
                    # Clear input like bash
                    event.app.current_buffer.reset()
                else:
                    self._should_exit.set()
                    event.app.exit()

        @kb.add("c-d")
        def _handle_ctrl_d(event):
            if not self._agent_running.is_set() and not input_area.text:
                self._should_exit.set()
                event.app.exit()

        # ── Layout ────────────────────────────────────────────────────────────
        status_bar = Window(
            content=FormattedTextControl(self._status_bar_fragments),
            height=1,
            style="class:status-bar",
        )

        # Completions menu for autocomplete display
        completions_menu = CompletionsMenu(max_height=12, scroll_offset=1)

        layout = Layout(
            HSplit([
                input_area,
                status_bar,
                completions_menu,
            ]),
            focused_element=input_area,
        )

        # ── Application ───────────────────────────────────────────────────────
        app: Application = Application(
            layout=layout,
            style=style,
            key_bindings=kb,
            full_screen=False,
            mouse_support=False,
            refresh_interval=0.2,
        )
        self._app = app

        def _show_help() -> None:
            cats = get_commands_by_category()
            for cat, cmds in cats.items():
                _cprint(f"\n{_DIM}{cat}{_RST}")
                for cmd in cmds:
                    aliases = (
                        f"  [{', '.join('/' + a for a in cmd.aliases)}]"
                        if cmd.aliases else ""
                    )
                    hint = f" {cmd.args_hint}" if cmd.args_hint else ""
                    _cprint(
                        f"  {_CYAN}/{cmd.name}{hint}{_RST}"
                        f"{_DIM}{aliases}  —  {cmd.description}{_RST}"
                    )

        # ── Spinner thread ────────────────────────────────────────────────────
        def _spinner_loop() -> None:
            import random
            verb_indices = list(range(len(THINKING_VERBS)))
            random.shuffle(verb_indices)
            vi = 0
            while not self._should_exit.is_set():
                if self._agent_running.is_set():
                    self._spinner_frame += 1
                    if self._spinner_frame % 10 == 0:
                        vi = (vi + 1) % len(verb_indices)
                        self._spinner_verb_idx = verb_indices[vi]
                    self._invalidate()
                    time.sleep(0.1)
                else:
                    time.sleep(0.2)

        spinner_thread = threading.Thread(target=_spinner_loop, daemon=True)
        spinner_thread.start()

        # ── Agent / process thread ────────────────────────────────────────────
        def _process_loop() -> None:
            while not self._should_exit.is_set():
                try:
                    text = _input_queue.get(timeout=0.1)
                except Exception:
                    continue

                # Slash command dispatch
                if text.startswith("/"):
                    parts = text[1:].split(None, 1)
                    cmd_name = parts[0].lower()
                    cmd_def = resolve_command(cmd_name)

                    if cmd_def is None:
                        _cprint(f"{_DIM}Unknown command: /{cmd_name}  (type /help){_RST}")
                        continue

                    if cmd_def.name in ("quit", "exit"):
                        self._should_exit.set()
                        app.exit()
                        return
                    if cmd_def.name == "help":
                        _show_help()
                        continue
                    if cmd_def.name == "clear":
                        import subprocess
                        subprocess.run(["clear"], check=False)
                        continue
                    # All other slash commands → agent (with user echo)

                # Echo the user message into scrollback so it's preserved
                _cprint(f"{_CYAN}❯ {text}{_RST}")

                self._interrupt_requested.clear()
                self._agent_running.set()
                self._invalidate()
                try:
                    on_input(text)
                finally:
                    self._agent_running.clear()
                    self._interrupt_requested.clear()
                    self._invalidate()

        process_thread = threading.Thread(target=_process_loop, daemon=True)
        process_thread.start()

        # ── Run the application inside patch_stdout ───────────────────────────
        with patch_stdout(), suppress(KeyboardInterrupt):
            app.run()

        self._should_exit.set()
        _cprint(f"{_DIM}Goodbye!{_RST}")

    def set_spinner(self, text: str) -> None:
        """Legacy compat — no-op; spinner is driven by _agent_running flag."""
        pass

    def update_context(self, tokens: int) -> None:
        self.context_tokens = tokens

    @property
    def is_running(self) -> bool:
        """True while the agent is processing a request."""
        return self._agent_running.is_set()

    @property
    def interrupt_requested(self) -> bool:
        """True if Ctrl+C was pressed while agent was running."""
        return self._interrupt_requested.is_set()


# Keep old names as stubs so existing imports don't break
class FooterSpinner:
    def __init__(self, *a, **kw): pass
    def start(self): pass
    def stop(self): pass

KawaiiSpinner = FooterSpinner


# ─── ANSI helpers ────────────────────────────────────────────────────────────

_RST   = "\033[0m"
_DIM   = "\033[2m"           # dim grey for thinking/meta text
_CYAN  = "\033[36m"          # user prompt / accent colour
_GOLD  = "\033[38;2;255;215;0m"   # warm gold for assistant response (matches Hermes)
_BOLD  = "\033[1m"

# ─── Streaming display ───────────────────────────────────────────────────────

_OPEN_TAGS  = ("<REASONING_SCRATCHPAD>", "<think>", "<reasoning>", "<THINKING>", "<thinking>", "<thought>")
_CLOSE_TAGS = ("</REASONING_SCRATCHPAD>", "</think>", "</reasoning>", "</THINKING>", "</thinking>", "</thought>")


def _cprint(text: str) -> None:
    """Print a line of ANSI text to the terminal.

    Inside the TUI, sys.stdout is prompt_toolkit's StdoutProxy (set by
    patch_stdout). Writing through print_formatted_text(ANSI(...)) ensures
    the text is injected above the TUI chrome without erasing the status bar.
    The event loop is never blocked (agent runs in a daemon thread), so the
    StdoutProxy flush queue is processed immediately.
    """
    try:
        from prompt_toolkit import print_formatted_text as _pt_print
        from prompt_toolkit.formatted_text import ANSI as _PT_ANSI
        _pt_print(_PT_ANSI(text))
    except Exception:
        try:
            sys.stdout.write(text + "\n")
            sys.stdout.flush()
        except (ValueError, OSError):
            pass


class StreamingReasoningBox:
    """Hermes-style streaming display.

    Thinking: └ ▼ Thinking ~N tokens / └─ dim text lines
    Response: │ plain text lines
    Tool calls: shown after response via print_tool_calls()

    All output via raw ANSI (no Rich markup) to avoid interleaving issues
    with the footer spinner's \\r writes.
    """

    def __init__(self, console=None):  # console kept for compat, unused
        self._reasoning_tokens = 0
        self._reasoning_lines: list[str] = []
        self._reasoning_buf = ""       # partial line buffer for reasoning
        self._response_buf = ""        # partial line buffer for response
        self._reasoning_opened = False
        self._response_opened = False
        self._in_reasoning = False
        self._prefilt_buf = ""
        self._last_was_newline = True
        self._deferred_content = ""

    # ── reasoning display ────────────────────────────────────────────────────

    def _open_reasoning(self) -> None:
        if self._reasoning_opened:
            return
        self._reasoning_opened = True
        # Header printed after we know token count — deferred to close

    def _close_reasoning(self) -> None:
        if not self._reasoning_opened:
            return
        self._reasoning_opened = False
        # Flush partial reasoning line
        if self._reasoning_buf.strip():
            self._reasoning_lines.append(self._reasoning_buf)
            self._reasoning_buf = ""
        if not self._reasoning_lines:
            return
        # Count tokens (rough word count)
        full_text = " ".join(self._reasoning_lines)
        self._reasoning_tokens = len(full_text.split())
        # Wrap text to terminal width like Hermes
        try:
            import textwrap
            w = shutil.get_terminal_size().columns
            wrap_w = max(40, w - 6)  # account for "  └─ " prefix
            wrapped: list[str] = []
            for raw in self._reasoning_lines:
                for wline in textwrap.wrap(raw, width=wrap_w) or [raw]:
                    wrapped.append(wline)
        except Exception:
            wrapped = self._reasoning_lines
        # Print Hermes-style header + indented dim lines
        _cprint(f"{_DIM}└ ▼ Thinking  ~{self._reasoning_tokens} tokens{_RST}")
        for i, line in enumerate(wrapped):
            is_last = i == len(wrapped) - 1
            prefix = "  └─" if is_last else "  ├─"
            _cprint(f"{_DIM}{prefix} {line}{_RST}")

    def _emit_reasoning(self, text: str) -> None:
        self._open_reasoning()
        self._reasoning_buf += text
        # Flush complete lines
        while "\n" in self._reasoning_buf:
            line, self._reasoning_buf = self._reasoning_buf.split("\n", 1)
            if line.strip():
                self._reasoning_lines.append(line)

    # ── response display ─────────────────────────────────────────────────────

    def _open_response(self) -> None:
        if self._response_opened:
            return
        self._response_opened = True
        # Close reasoning first
        self._close_reasoning()

    def _emit_response(self, text: str) -> None:
        if self._reasoning_opened:
            self._deferred_content += text
            return
        self._close_reasoning()
        self._open_response()
        self._response_buf += text
        # Flush every complete line immediately via _cprint (which adds \n and
        # triggers StdoutProxy to inject the text above the TUI chrome).
        while "\n" in self._response_buf:
            line, self._response_buf = self._response_buf.split("\n", 1)
            _cprint(f"{_GOLD}│{_RST} {line}")

    # ── tag filtering (same logic as before) ─────────────────────────────────

    def _is_block_boundary(self, preceding: str) -> bool:
        if not preceding:
            return self._last_was_newline
        last_nl = preceding.rfind("\n")
        if last_nl == -1:
            return self._last_was_newline and preceding.strip() == ""
        return preceding[last_nl + 1:].strip() == ""

    def feed(self, text: str) -> str:
        if not text:
            return ""
        self._prefilt_buf += text
        if not self._in_reasoning:
            for tag in _OPEN_TAGS:
                idx = self._prefilt_buf.find(tag)
                if idx == -1:
                    continue
                preceding = self._prefilt_buf[:idx]
                if not self._is_block_boundary(preceding):
                    continue
                if preceding:
                    self._emit_response(preceding)
                    self._last_was_newline = preceding.endswith("\n")
                self._in_reasoning = True
                self._prefilt_buf = self._prefilt_buf[idx + len(tag):]
                break
            else:
                safe = self._prefilt_buf
                for tag in _OPEN_TAGS:
                    for i in range(1, len(tag)):
                        if self._prefilt_buf.endswith(tag[:i]):
                            safe = self._prefilt_buf[:-i]
                            break
                if safe:
                    self._emit_response(safe)
                    self._last_was_newline = safe.endswith("\n")
                    self._prefilt_buf = self._prefilt_buf[len(safe):]
                return ""

        for tag in _CLOSE_TAGS:
            idx = self._prefilt_buf.find(tag)
            if idx != -1:
                self._in_reasoning = False
                inner = self._prefilt_buf[:idx]
                if inner:
                    self._emit_reasoning(inner)
                after = self._prefilt_buf[idx + len(tag):]
                self._prefilt_buf = ""
                if after:
                    return self.feed(after)
                return ""

        max_tag_len = max(len(t) for t in _CLOSE_TAGS)
        if len(self._prefilt_buf) > max_tag_len:
            self._emit_reasoning(self._prefilt_buf[:-max_tag_len])
            self._prefilt_buf = self._prefilt_buf[-max_tag_len:]
        return ""

    def feed_reasoning(self, text: str) -> None:
        """Feed reasoning from API delta.reasoning field (not inline tags)."""
        if text:
            self._emit_reasoning(text)

    def flush(self) -> None:
        """Flush all buffers and close open boxes at end of stream."""
        # False positive recovery
        if self._in_reasoning and self._prefilt_buf:
            self._in_reasoning = False
            self._emit_response(self._prefilt_buf)
            self._prefilt_buf = ""
        self._close_reasoning()
        if self._deferred_content:
            self._emit_response(self._deferred_content)
            self._deferred_content = ""
        # Flush any remaining partial line
        if self._response_buf.strip():
            _cprint(f"{_GOLD}│{_RST} {self._response_buf}")
            self._response_buf = ""

    def reset(self) -> None:
        self._reasoning_tokens = 0
        self._reasoning_lines = []
        self._reasoning_buf = ""
        self._response_buf = ""
        self._reasoning_opened = False
        self._response_opened = False
        self._in_reasoning = False
        self._prefilt_buf = ""
        self._last_was_newline = True
        self._deferred_content = ""


def print_tool_calls(tool_names: list[str]) -> None:
    """Print Hermes-style tool call summary: └ ▼ Tool calls (N)."""
    if not tool_names:
        return
    _cprint(f"{_DIM}└ ▼ Tool calls ({len(tool_names)}){_RST}")
    for i, name in enumerate(tool_names):
        prefix = "  └─" if i == len(tool_names) - 1 else "  ├─"
        _cprint(f"{_DIM}{prefix} ● {name}{_RST}")
    _cprint("")  # blank line before response


# ─── Footer / Status Bar ────────────────────────────────────────────────────

def print_footer(console, model: str, elapsed: float,
                 context_tokens: int = 0, context_window: int = 0) -> None:
    """Print Hermes-style status footer: – ready | model | ctx | bar | elapsed"""
    model_short = model.split("/")[-1] if "/" in model else model

    # Format elapsed like Hermes: 1m 30s or 45s
    e = int(elapsed)
    elapsed_str = f"{e // 60}m {e % 60}s" if e >= 60 else f"{e}s"

    parts = ["– ready", model_short]

    if context_window > 0:
        pct = int((context_tokens / context_window) * 100)
        bar_w = 14
        filled = round((pct / 100) * bar_w)
        bar = "█" * filled + "░" * (bar_w - filled)
        # Format like Hermes: 15.5k/128k
        def _fmt(n: int) -> str:
            return f"{n / 1000:.1f}k" if n >= 1000 else str(n)
        parts.append(f"{_fmt(context_tokens)}/{_fmt(context_window)}")
        parts.append(f"[{bar}] {pct}%")

    parts.append(elapsed_str)
    line = " | ".join(parts)
    _cprint(f"{_DIM}{line}{_RST}")
