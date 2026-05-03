"""Delegation tool — spawn sub-agents to handle tasks.

Allows an orchestrator agent to delegate tasks to child agents that run
in worker threads with explicit budgets and hard timeouts.

Design principles:
- Isolated context by default (fresh conversation per sub-agent)
- Depth-based role system (orchestrator vs. leaf)
- Explicit token/iteration budgets at every layer
- Thread-safe execution via ThreadPoolExecutor
- Hard timeout enforcement (max 300s)
"""

import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

import httpx

from nova.tools.registry import registry

logger = logging.getLogger(__name__)

# Maximum allowed timeout for any sub-agent
MAX_TIMEOUT_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_ITERATIONS = 30


DELEGATE_TASK_SCHEMA = {
    "name": "delegate_task",
    "description": (
        "Spawn a sub-agent to handle a specific task. "
        "Use for tasks that can be isolated, parallelized, or require focused execution. "
        "The sub-agent has access to all tools except delegate_task (if at depth limit). "
        "Returns a JSON result with success status, output, and budget usage."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Clear description of the task for the sub-agent to complete.",
            },
            "label": {
                "type": "string",
                "description": "Optional short label for logging/display (e.g. 'lint check').",
            },
            "model": {
                "type": "string",
                "description": (
                    "Optional model override (e.g. 'openai/gpt-4o-mini' for cheaper tasks). "
                    "Defaults to parent's model."
                ),
            },
            "timeout_seconds": {
                "type": "integer",
                "description": f"Timeout in seconds (default {DEFAULT_TIMEOUT_SECONDS}, max {MAX_TIMEOUT_SECONDS}).",
            },
            "context_mode": {
                "type": "string",
                "enum": ["isolated", "fork"],
                "description": (
                    "Context mode: 'isolated' (fresh conversation, default) or "
                    "'fork' (inherit parent transcript for context-aware tasks)."
                ),
            },
        },
        "required": ["task"],
    },
}


def _build_subagent_config(
    parent_config: dict,
    depth: int,
    model: str | None,
    max_iterations: int,
) -> dict:
    """Build a config dict for the sub-agent, inheriting from parent."""
    import copy

    config = copy.deepcopy(parent_config)

    # Override model if specified
    if model:
        config["openrouter"]["model"] = model

    # Set sub-agent depth
    config["_subagent_depth"] = depth

    # Apply sub-agent budget overrides from delegation config.
    # Config value wins; max_iterations argument is the fallback default.
    delegation = config.get("delegation", {})
    subagent_budgets = delegation.get("subagent_budgets", {})

    config["agent"]["max_iterations"] = subagent_budgets.get("max_iterations", max_iterations)

    if "system_prompt_max" in subagent_budgets:
        config["budgets"]["system_prompt_max"] = subagent_budgets["system_prompt_max"]
    if "context_total_max_chars" in subagent_budgets:
        config["budgets"]["context_total_max_chars"] = subagent_budgets["context_total_max_chars"]
    if "tool_result_max_chars" in subagent_budgets:
        config["budgets"]["tool_result_max_chars"] = subagent_budgets["tool_result_max_chars"]

    # Sub-agents use minimal prompt mode (no skills index, no context files)
    # to keep their context window focused on the task
    config["_prompt_mode"] = "minimal"

    return config


def _run_subagent(
    task: str,
    parent_agent: Any,
    label: str,
    model: str | None,
    timeout_seconds: int,
    context_mode: str,
) -> dict:
    """Core sub-agent execution logic (runs in worker thread)."""
    # Import here to avoid circular imports at module level
    from nova.agent import NovaAgent

    depth = getattr(parent_agent, "depth", 0) + 1
    task_id = str(uuid.uuid4())[:8]
    log_prefix = f"[subagent:{label}:{task_id}]"

    logger.info("%s spawning at depth=%d, timeout=%ds", log_prefix, depth, timeout_seconds)
    start_time = time.monotonic()

    # Build sub-agent config
    delegation_cfg = parent_agent.config.get("delegation", {})
    max_iterations = delegation_cfg.get("subagent_budgets", {}).get(
        "max_iterations", DEFAULT_MAX_ITERATIONS,
    )
    subagent_config = _build_subagent_config(
        parent_config=parent_agent.config,
        depth=depth,
        model=model,
        max_iterations=max_iterations,
    )

    # Build initial messages based on context mode
    if context_mode == "fork" and parent_agent.messages:
        # Inherit parent transcript — sub-agent has full context
        prefill_messages = list(parent_agent.messages)
        logger.debug("%s using fork context (%d messages)", log_prefix, len(prefill_messages))
    else:
        # Fresh conversation — sub-agent starts clean
        prefill_messages = []
        logger.debug("%s using isolated context", log_prefix)

    try:
        # Create a new HTTP client for the sub-agent — httpx.Client is not
        # thread-safe for concurrent use, so we cannot share the parent's client.
        openrouter_cfg = subagent_config["openrouter"]
        subagent_http_client = httpx.Client(
            base_url=openrouter_cfg["base_url"],
            headers={
                "Authorization": f"Bearer {openrouter_cfg['api_key']}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://nova-agent.local",
                "X-Title": "Nova Agent",
            },
            timeout=120.0,
        )
        subagent = NovaAgent(
            config=subagent_config,
            http_client=subagent_http_client,
            session_store=parent_agent.session_store,
            memory_store=parent_agent.memory,
        )

        # Inject prefill messages if forking
        if prefill_messages:
            subagent.messages = prefill_messages

        # Run the task
        result = subagent.run(task, stream=False)

        elapsed = time.monotonic() - start_time
        # Count messages to estimate iterations (each tool round = 2 messages: assistant + tool)
        tool_msgs = sum(1 for m in subagent.messages if m.get("role") == "tool")
        logger.info(
            "%s completed in %.1fs, ~%d tool calls",
            log_prefix, elapsed, tool_msgs,
        )

        return {
            "success": True,
            "result": result,
            "label": label,
            "depth": depth,
            "elapsed_seconds": round(elapsed, 1),
            "error": None,
            "timeout": False,
        }

    except Exception as e:
        elapsed = time.monotonic() - start_time
        logger.error("%s failed after %.1fs: %s", log_prefix, elapsed, e)
        return {
            "success": False,
            "result": None,
            "label": label,
            "depth": depth,
            "elapsed_seconds": round(elapsed, 1),
            "error": str(e),
            "timeout": False,
        }


def _delegate_task(args: dict[str, Any], **kwargs) -> str:
    """Handler for the delegate_task tool."""
    agent = kwargs.get("agent")
    if agent is None:
        return json.dumps({"success": False, "error": "No agent context available."})

    task = args.get("task", "").strip()
    if not task:
        return json.dumps({"success": False, "error": "Task description is required."})

    label = args.get("label") or task[:40].replace("\n", " ")
    model = args.get("model")
    context_mode = args.get("context_mode", "isolated")
    # Read default timeout from config, fall back to module constant
    config_default_timeout = agent.config.get("delegation", {}).get(
        "default_timeout_seconds", DEFAULT_TIMEOUT_SECONDS,
    )
    timeout_seconds = min(
        int(args.get("timeout_seconds", config_default_timeout)),
        MAX_TIMEOUT_SECONDS,
    )

    # Validate context_mode
    if context_mode not in ("isolated", "fork"):
        context_mode = "isolated"

    # Check depth limit
    depth = getattr(agent, "depth", 0)
    max_spawn_depth = agent.config.get("delegation", {}).get("max_spawn_depth", 2)
    if depth >= max_spawn_depth:
        return json.dumps({
            "success": False,
            "error": (
                f"Cannot spawn sub-agent: already at max depth ({depth}/{max_spawn_depth}). "
                "This agent is a leaf and cannot delegate further."
            ),
        })

    # Run sub-agent in worker thread with hard timeout
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            _run_subagent,
            task=task,
            parent_agent=agent,
            label=label,
            model=model,
            timeout_seconds=timeout_seconds,
            context_mode=context_mode,
        )
        try:
            result = future.result(timeout=timeout_seconds)
        except FuturesTimeoutError:
            logger.warning("Sub-agent '%s' timed out after %ds", label, timeout_seconds)
            result = {
                "success": False,
                "result": None,
                "label": label,
                "depth": depth + 1,
                "elapsed_seconds": timeout_seconds,
                "error": f"Sub-agent timed out after {timeout_seconds}s.",
                "timeout": True,
            }

    return json.dumps(result, indent=2)


def _is_delegation_enabled(config: dict | None = None) -> bool:
    """Check if delegation is enabled in config."""
    if config is None:
        return False
    return config.get("delegation", {}).get("enabled", False)


def register_delegate_tool(agent_config: dict | None = None) -> None:
    """Register the delegate_task tool if delegation is enabled and agent is not a leaf.

    Gating rules (both must be true):
    - delegation.enabled is True in config
    - _subagent_depth < delegation.max_spawn_depth (not a leaf agent)

    Called from discover_builtin_tools() with the agent's config.
    """
    if not _is_delegation_enabled(agent_config):
        logger.debug("Delegation disabled — skipping delegate_task registration")
        return

    cfg = agent_config or {}
    depth = cfg.get("_subagent_depth", 0)
    max_depth = cfg.get("delegation", {}).get("max_spawn_depth", 2)
    if depth >= max_depth:
        logger.debug(
            "Agent at depth %d >= max_spawn_depth %d — skipping delegate_task (leaf agent)",
            depth, max_depth,
        )
        return

    registry.register(
        name="delegate_task",
        toolset="delegation",
        schema=DELEGATE_TASK_SCHEMA,
        handler=_delegate_task,
        emoji="🤖",
    )
    logger.debug("Registered tool: delegate_task")
