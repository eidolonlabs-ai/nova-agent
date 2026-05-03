"""Tests for the cost tracker."""

from nova.cost_tracker import (
    _MODEL_PRICING,
    CostTracker,
    UsageSnapshot,
    extract_usage_from_response,
)

# ── UsageSnapshot ───────────────────────────────────────────────────────────


def test_usage_snapshot_totals():
    snap = UsageSnapshot(input_tokens=1000, output_tokens=500, input_cost=0.001, output_cost=0.002)
    assert snap.total_tokens == 1500
    assert snap.total_cost == 0.003


def test_usage_snapshot_defaults():
    snap = UsageSnapshot()
    assert snap.total_tokens == 0
    assert snap.total_cost == 0.0


# ── CostTracker — Basic Usage ───────────────────────────────────────────────


def test_add_usage_tokens_only():
    tracker = CostTracker(model="qwen/qwen3.6-flash")
    tracker.add_usage(input_tokens=1000, output_tokens=500)
    assert tracker.total.input_tokens == 1000
    assert tracker.total.output_tokens == 500


def test_add_usage_with_costs():
    tracker = CostTracker(model="qwen/qwen3.6-flash")
    tracker.add_usage(input_tokens=1000, output_tokens=500, input_cost=0.00003, output_cost=0.000045)
    assert tracker.total.input_cost == 0.00003
    assert tracker.total.output_cost == 0.000045


def test_add_usage_cumulative():
    tracker = CostTracker(model="qwen/qwen3.6-flash")
    tracker.add_usage(input_tokens=1000, output_tokens=500)
    tracker.add_usage(input_tokens=2000, output_tokens=1000)
    assert tracker.total.input_tokens == 3000
    assert tracker.total.output_tokens == 1500


def test_add_usage_cumulative_costs():
    tracker = CostTracker(model="qwen/qwen3.6-flash")
    tracker.add_usage(input_tokens=1000, output_tokens=500, input_cost=0.00003, output_cost=0.000045)
    tracker.add_usage(input_tokens=2000, output_tokens=1000, input_cost=0.00006, output_cost=0.00009)
    assert abs(tracker.total.input_cost - 0.00009) < 1e-10
    assert abs(tracker.total.output_cost - 0.000135) < 1e-10


def test_cost_estimation_from_model_pricing():
    tracker = CostTracker(model="qwen/qwen3.6-flash")
    tracker.add_usage(input_tokens=1_000_000, output_tokens=1_000_000)
    # qwen3.6-flash: $0.03/1M input, $0.09/1M output
    assert abs(tracker.total.input_cost - 0.03) < 1e-10
    assert abs(tracker.total.output_cost - 0.09) < 1e-10


def test_cost_estimation_unknown_model_uses_default():
    tracker = CostTracker(model="unknown/model")
    tracker.add_usage(input_tokens=1_000_000, output_tokens=1_000_000)
    # Default: $0.10/1M input, $0.30/1M output
    assert abs(tracker.total.input_cost - 0.10) < 1e-10
    assert abs(tracker.total.output_cost - 0.30) < 1e-10


def test_reset_tracker():
    tracker = CostTracker(model="qwen/qwen3.6-flash")
    tracker.add_usage(input_tokens=1000, output_tokens=500, input_cost=0.001, output_cost=0.002)
    tracker.reset()
    assert tracker.total.input_tokens == 0
    assert tracker.total.output_tokens == 0
    assert tracker.total.input_cost == 0.0
    assert tracker.total.output_cost == 0.0


def test_format_summary():
    tracker = CostTracker(model="qwen/qwen3.6-flash")
    tracker.add_usage(input_tokens=1000, output_tokens=500, input_cost=0.00003, output_cost=0.000045)
    summary = tracker.format_summary()
    assert "1,500" in summary
    assert "1,000" in summary
    assert "500" in summary
    assert "$" in summary


def test_format_summary_no_cost():
    tracker = CostTracker(model="qwen/qwen3.6-flash")
    tracker.add_usage(input_tokens=1000, output_tokens=500, input_cost=0.0, output_cost=0.0)
    summary = tracker.format_summary()
    assert "Tokens:" in summary
    assert "Cost:" not in summary


# ── extract_usage_from_response ─────────────────────────────────────────────


def test_extract_usage_from_response():
    response = {
        "usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
        }
    }
    usage = extract_usage_from_response(response)
    assert usage["input_tokens"] == 1000
    assert usage["output_tokens"] == 500


def test_extract_usage_from_response_with_cost():
    response = {
        "usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "cost": 0.000075,
        }
    }
    usage = extract_usage_from_response(response)
    assert usage["input_tokens"] == 1000
    assert usage["output_tokens"] == 500
    assert usage["output_cost"] == 0.000075


def test_extract_usage_from_response_empty():
    response = {}
    usage = extract_usage_from_response(response)
    assert usage["input_tokens"] == 0
    assert usage["output_tokens"] == 0


# ── Model Pricing Table ─────────────────────────────────────────────────────


def test_model_pricing_has_entries():
    assert len(_MODEL_PRICING) > 0
    assert "qwen/qwen3.6-flash" in _MODEL_PRICING
    assert "openai/gpt-4o" in _MODEL_PRICING


def test_model_pricing_structure():
    for _model, pricing in _MODEL_PRICING.items():
        assert "input" in pricing
        assert "output" in pricing
        assert pricing["input"] > 0
        assert pricing["output"] > 0
