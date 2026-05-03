"""System prompt assembly.

Assembles the system prompt from layers with explicit token budgets.
Supports full/minimal/none modes for prompt gating.
"""

import logging
from pathlib import Path

from nova.context import build_context_prompt
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

# Tool-use enforcement (concise version — no overlap with identity)
TOOL_USE_GUIDANCE = (
    "Use tools to take action — don't describe what you would do. "
    "Every response should either contain tool calls or deliver a final result."
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
MEMORY_GUIDANCE = (
    "Save durable facts using the memory tool: user preferences, environment details, tool quirks. "
    "Write memories as declarative facts, not instructions. "
    "Do NOT save task progress or temporary state."
)


def build_system_prompt(
    config: dict,
    cwd: Path | None = None,
    mode: str = "full",
    memory_content: str | None = None,
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

    # 1. Identity
    identity = agent_config.get("identity", DEFAULT_IDENTITY)
    parts.append(identity)

    # 2. Tool summary (compact bullet list — two-tier approach)
    tool_summary = registry.get_tool_summary_list()
    if tool_summary:
        parts.append(f"## Available Tools\n{tool_summary}")
        parts.append(TOOL_USE_GUIDANCE)

    # 2b. Delegation guidance — orchestrators get how-to, leaves get a reminder
    depth = config.get("_subagent_depth", 0)
    max_spawn_depth = config.get("delegation", {}).get("max_spawn_depth", 2)
    delegation_enabled = config.get("delegation", {}).get("enabled", False)
    if delegation_enabled:
        if depth < max_spawn_depth:
            parts.append(DELEGATION_GUIDANCE)
        else:
            parts.append(LEAF_AGENT_GUIDANCE)

    # 3. Memory guidance (only if memory is enabled)
    if config.get("memory", {}).get("enabled"):
        parts.append(MEMORY_GUIDANCE)

    # 4. Memory content (prefetched facts)
    if memory_content:
        parts.append(memory_content)

    # 5. Skills index (full mode only)
    if mode == "full" and config.get("skills", {}).get("enabled"):
        skills_dir = Path(config["skills"]["directory"]).expanduser()
        skills = discover_skills(
            skills_dir,
            max_count=budgets.get("skills_max_count", 50),
            max_chars=budgets.get("skills_max_chars", 15000),
        )
        skills_prompt = build_skills_prompt(skills, max_chars=budgets.get("skills_max_chars", 15000))
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

    # 7. Current date/time
    from datetime import datetime
    parts.append(f"Current date: {datetime.now().strftime('%A, %B %d, %Y')}")

    # 8. Model info
    model = config.get("openrouter", {}).get("model", "unknown")
    parts.append(f"Model: {model}")

    result = "\n\n".join(p.strip() for p in parts if p.strip())

    # Enforce total budget
    max_tokens = budgets.get("system_prompt_max", 8000)
    current_tokens = estimate_tokens(result)
    if current_tokens > max_tokens:
        logger.warning(
            "System prompt exceeds budget: %d > %d tokens — truncating",
            current_tokens, max_tokens,
        )
        # Truncate from the end (context files are last)
        chars_to_keep = int(len(result) * max_tokens / current_tokens)
        result = result[:chars_to_keep] + "\n\n[...system prompt truncated to fit budget...]"

    return result
