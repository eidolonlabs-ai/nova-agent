"""Cost tracking — token counts and dollar costs per session.

Tracks cumulative input/output tokens and estimated dollar costs
based on per-model pricing from OpenRouter response headers.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# Approximate per-model pricing (USD per 1M tokens)
# Sourced from OpenRouter pricing. These are defaults — actual costs
# come from OpenRouter response headers when available.
_MODEL_PRICING: dict[str, dict[str, float]] = {
    "qwen/qwen3.6-flash": {"input": 0.03, "output": 0.09},
    "qwen/qwen3.5-flash": {"input": 0.03, "output": 0.09},
    "qwen/qwen3-235b-a22b": {"input": 0.10, "output": 0.30},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/o3-mini": {"input": 1.10, "output": 4.40},
    "anthropic/claude-3.5-haiku": {"input": 0.80, "output": 4.00},
    "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "anthropic/claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "google/gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "google/gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "meta-llama/llama-3.3-70b-instruct": {"input": 0.12, "output": 0.30},
    "meta-llama/llama-4-maverick": {"input": 0.20, "output": 0.80},
}

# Default pricing for unknown models (cheap model assumption)
_DEFAULT_PRICING = {"input": 0.10, "output": 0.30}


@dataclass
class UsageSnapshot:
    """Immutable snapshot of usage at a point in time."""

    input_tokens: int = 0
    output_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def total_cost(self) -> float:
        return self.input_cost + self.output_cost


@dataclass
class CostTracker:
    """Tracks cumulative token usage and dollar costs for a session.

    Usage:
        tracker = CostTracker(model="qwen/qwen3.6-flash")
        tracker.add_usage(input_tokens=1000, output_tokens=500)
        # Or with OpenRouter header costs:
        tracker.add_usage(input_tokens=1000, output_tokens=500,
                          input_cost=0.00003, output_cost=0.000045)
        print(tracker.total.total_cost)  # 0.000075
    """

    model: str = ""
    _usage: UsageSnapshot = field(default_factory=UsageSnapshot)

    def add_usage(
        self,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        input_cost: float | None = None,
        output_cost: float | None = None,
    ) -> None:
        """Add usage from an API response.

        If costs are not provided, they are estimated from the model's
        pricing table.
        """
        if input_cost is None or output_cost is None:
            estimated = self._estimate_cost(input_tokens, output_tokens)
            if input_cost is None:
                input_cost = estimated["input"]
            if output_cost is None:
                output_cost = estimated["output"]

        self._usage = UsageSnapshot(
            input_tokens=self._usage.input_tokens + input_tokens,
            output_tokens=self._usage.output_tokens + output_tokens,
            input_cost=self._usage.input_cost + input_cost,
            output_cost=self._usage.output_cost + output_cost,
        )

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> dict[str, float]:
        """Estimate dollar cost from token counts using model pricing."""
        pricing = _MODEL_PRICING.get(self.model, _DEFAULT_PRICING)
        return {
            "input": input_tokens * pricing["input"] / 1_000_000,
            "output": output_tokens * pricing["output"] / 1_000_000,
        }

    @property
    def total(self) -> UsageSnapshot:
        """Return the current cumulative usage snapshot."""
        return self._usage

    def reset(self) -> None:
        """Reset the tracker to zero."""
        self._usage = UsageSnapshot()

    def format_summary(self) -> str:
        """Return a human-readable usage summary."""
        t = self.total
        lines = [
            f"Tokens: {t.total_tokens:,} total ({t.input_tokens:,} in, {t.output_tokens:,} out)",
        ]
        if t.total_cost > 0:
            lines.append(
                f"Cost: ${t.total_cost:.6f} (${t.input_cost:.6f} in, ${t.output_cost:.6f} out)"
            )
        return " | ".join(lines)


def extract_usage_from_response(response_data: dict) -> dict[str, int]:
    """Extract token usage from an OpenRouter API response.

    OpenRouter returns usage in the response body under 'usage' key.
    Also checks for cost headers.

    Returns dict with input_tokens, output_tokens, and optionally
    input_cost, output_cost from headers.
    """
    usage = response_data.get("usage", {})
    result: dict[str, int] = {
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
    }

    # OpenRouter may include cost in the usage dict
    if "cost" in usage:
        result["output_cost"] = usage["cost"]  # type: ignore[assignment]

    return result  # type: ignore[return-value]
