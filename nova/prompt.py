"""System prompt assembly.

Assembles the system prompt from layers with explicit token budgets.
Supports full/minimal/none modes for prompt gating.
"""

import logging
from pathlib import Path

from nova.context import build_context_prompt, load_global_personality
from nova.skills import build_skills_prompt, discover_skills
from nova.tokens import estimate_tokens
from nova.tools.registry import registry

logger = logging.getLogger(__name__)

# Default agent identity
DEFAULT_IDENTITY = (
    "You are Nova, a helpful personal assistant. "
    "You are direct, efficient, and focused on being genuinely useful. "
    "Admit uncertainty when appropriate. Prioritize action over explanation."
)

# Tool-use enforcement
TOOL_USE_GUIDANCE = (
    "## Tool-use Rules\n"
    "- Use tools to take action — never describe what you *would* do without doing it.\n"
    "- When you say you will run a command, read a file, or search the web, make the "
    "tool call immediately in the same response.\n"
    "- Never end a turn with a promise of future action — execute it now.\n"
    "- Keep working until the task is actually complete and verified.\n"
    "- Every response must either (a) make tool calls that make progress, or "
    "(b) deliver a final result. Responses that only describe intentions are not acceptable."
)

# Model-specific enforcement for models known to describe instead of act
_TOOL_ENFORCEMENT_MODELS = ("gpt", "codex", "gemini", "gemma", "grok", "o1", "o3", "o4")

EXECUTION_DISCIPLINE = (
    "## Execution Discipline\n"
    "- Do not stop early when another tool call would improve the result.\n"
    "- If a tool returns empty or partial results, retry with a different query.\n"
    "- Before finalizing: verify correctness, check that all requirements are met.\n"
    "- If required context is missing, use a lookup tool — do not guess or hallucinate.\n"
    "- For math, hashes, dates, file contents, or system state: always use a tool, never compute from memory."
)

# Delegation guidance (orchestrator agents only)
DELEGATION_GUIDANCE = (
    "## Task Delegation\n"
    "Use delegate_task to hand off isolated or parallelizable work to a focused sub-agent.\n"
    "Good candidates: tasks that are independent, can run in parallel, or need a clean context.\n"
    "Bad candidates: tasks that require back-and-forth with the user or depend on prior tool results.\n"
    "Tips:\n"
    "- Write a clear, self-contained task description — the sub-agent has no other context by default.\n"
    "- Use context_mode='fork' only when the sub-agent needs the full conversation history.\n"
    "- Use model= to pick a cheaper model for simple sub-tasks.\n"
    "- Aggregate all sub-agent results into your final response."
)

# Leaf-agent guidance (sub-agents at max depth)
LEAF_AGENT_GUIDANCE = (
    "## Focused Sub-Agent Mode\n"
    "You are a focused sub-agent. Complete the assigned task directly using available tools. "
    "Do not attempt to delegate — handle everything yourself."
)

# Memory guidance (minimal)
WIKI_GUIDANCE = """## Wiki Knowledge Base

Manage a persistent wiki of Obsidian-compatible markdown notes via the `wiki` tool. Build it up over time so future sessions can recall what you've learned.

### Folder conventions
- `Core/<topic>` — always-in-context facts (user identity, preferences, environment). Full content auto-injected every turn — keep short and high-signal.
- `People/<Name>` — facts about users and collaborators
- `Projects/<name>` — project state, decisions, conventions, gotchas
- `Facts/<topic>` — durable technical knowledge, references
- `Concepts/<name>` — definitions, mental models

### Frontmatter flags
- `inject: true` — pin any note into the system prompt (full content, like Core/). Use for active-project context that lives outside Core/.

### Write rules
- SEARCH first — run `wiki search` before writing. If a related note exists, `append` or update rather than creating a duplicate.
- Save user preferences, identity, and recurring context to `Core/` so they appear in every prompt.
- Use `[[wikilinks]]` liberally to connect related notes, and `#tags` for cross-cutting context.
- Save durable knowledge only — never task progress, todos, conversation context, or daily-changing state.
- When new info contradicts a note, UPDATE it (write with same title). When it extends, APPEND. Never create dated snapshots.

### Actions reference
| Action | What it does |
|--------|-------------|
| `write` | Create or overwrite a note (title, content, tags) |
| `append` | Add content to a note without overwriting |
| `read` | Fetch full note content |
| `search` | Full-text search across all notes |
| `list` | List notes sorted by recency, optionally filtered by tag |
| `delete` | Remove a note (warns if backlinks exist) |
| `rename` | Rename a note and update all [[wikilinks]] that point to it |
| `list_tags` | Return all tags with usage counts |
| `rename_tag` | Rename a tag globally across all notes |
| `follow` | BFS graph traversal via [[wikilinks]] (depth, max_notes, include_content). Pure Python — zero extra LLM calls. Set include_content:true to read a full neighbourhood in one shot. |
| `backlinks` | Find all notes that link to a given title |
| `maintenance` | Read-only report: duplicates, broken links, orphans, stale notes |

### Maintenance
- Run `wiki maintenance` periodically. The report surfaces:
  - `broken_links` — wikilinks pointing to notes that don't exist (fix with `rename` or `write`)
  - `duplicate_candidates` — notes with similar titles (merge with `write`+`delete`)
  - `orphans` — notes with no links in or out (connect or delete)
  - `stale` — notes not updated in 90+ days (review or archive)
- The report is read-only — act on it by updating notes or asking the user. Do not auto-delete.
- Before deleting a note, use `backlinks` to check what links to it. Use `rename` instead of delete+rewrite to preserve link integrity.
"""


def _build_wiki_guidance(config: dict) -> str:
    """Return WIKI_GUIDANCE with the vault path injected."""
    vault_path = config.get("wiki", {}).get("vault_path", "~/.nova/wiki")
    vault_abs = str(Path(vault_path).expanduser())
    return (
        WIKI_GUIDANCE
        + f"\n**Vault location:** `{vault_abs}` — "
        "always use the `wiki` tool to read/write notes (not `read_file`/`write_file`).\n"
    )


def build_system_prompt(
    config: dict,
    cwd: Path | None = None,
    mode: str = "full",
    wiki_content: str | None = None,
) -> str:
    """Assemble the full system prompt from all layers.

    Modes:
    - "full": Main agent — all layers
    - "minimal": Sub-agent — identity + tools + workspace only
    - "none": Bare minimum — identity only
    """
    budgets = config.get("budgets", {})
    agent_config = config.get("agent", {})

    if mode == "none":
        return agent_config.get("identity", DEFAULT_IDENTITY)

    parts = []

    # 1. Identity (try global personality first, fall back to config)
    global_personality = load_global_personality()
    identity = global_personality or agent_config.get("identity", DEFAULT_IDENTITY)
    parts.append(identity)

    # 2. Tool summary (compact bullet list — two-tier approach)
    tool_summary = registry.get_tool_summary_list()
    if tool_summary:
        parts.append(f"## Available Tools\n{tool_summary}")
        parts.append(TOOL_USE_GUIDANCE)

    # 2b. Model-specific execution discipline for models prone to describing vs acting
    model = config.get("openrouter", {}).get("model", "").lower()
    if any(m in model for m in _TOOL_ENFORCEMENT_MODELS):
        parts.append(EXECUTION_DISCIPLINE)

    # 2c. Delegation guidance — orchestrators get how-to, leaves get a reminder
    depth = config.get("_subagent_depth", 0)
    max_spawn_depth = config.get("delegation", {}).get("max_spawn_depth", 2)
    delegation_enabled = config.get("delegation", {}).get("enabled", False)
    if delegation_enabled:
        if depth < max_spawn_depth:
            parts.append(DELEGATION_GUIDANCE)
        else:
            parts.append(LEAF_AGENT_GUIDANCE)

    # 3. Wiki memory index (guidance + content adjacent so model sees rules before notes)
    if wiki_content:
        if config.get("wiki", {}).get("enabled"):
            parts.append(_build_wiki_guidance(config))
        parts.append(wiki_content)
    elif config.get("wiki", {}).get("enabled"):
        parts.append(_build_wiki_guidance(config))

    # 5. Skills index (full mode only)
    if mode == "full" and config.get("skills", {}).get("enabled"):
        skills_dir = Path(config["skills"]["directory"]).expanduser()
        skills = discover_skills(
            skills_dir,
            max_count=budgets.get("skills_max_count", 50),
            max_chars=budgets.get("skills_max_chars", 15000),
        )
        skills_prompt = build_skills_prompt(
            skills, max_chars=budgets.get("skills_max_chars", 15000)
        )
        if skills_prompt:
            parts.append(skills_prompt)

    # 6. Context files (full mode only)
    if mode == "full":
        context_prompt = build_context_prompt(
            cwd=cwd,
            file_names=config.get("context_files"),
            max_chars_per_file=budgets.get("context_file_max_chars", 10000),
            max_total_chars=budgets.get("context_total_max_chars", 50000),
        )
        if context_prompt:
            parts.append(context_prompt)

    # 7. Current date (ISO format — unambiguous and token-efficient)
    from datetime import date

    parts.append(f"Today: {date.today().isoformat()}")

    # 8. Model info
    current_model = config.get("openrouter", {}).get("model", "unknown")
    parts.append(f"Model: {current_model}")

    result = "\n\n".join(p.strip() for p in parts if p.strip())

    # Enforce total budget: drop optional layers (skills, context) before truncating
    max_tokens = budgets.get("system_prompt_max", 8000)
    current_tokens = estimate_tokens(result)
    if current_tokens > max_tokens:
        logger.warning(
            "System prompt exceeds budget: %d > %d tokens — rebuilding without context files",
            current_tokens,
            max_tokens,
        )
        # Rebuild without context files first
        core_parts = [p for p in parts if not p.startswith("# Project Context")]
        result = "\n\n".join(p.strip() for p in core_parts if p.strip())
        current_tokens = estimate_tokens(result)

    if current_tokens > max_tokens:
        logger.warning(
            "System prompt still exceeds budget after dropping context: %d > %d tokens — truncating",
            current_tokens,
            max_tokens,
        )
        chars_to_keep = int(len(result) * max_tokens / current_tokens)
        result = result[:chars_to_keep] + "\n\n[...system prompt truncated to fit budget...]"

    return result
