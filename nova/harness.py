"""In-memory run and tool traces for the harness contract."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Literal

VerificationStatus = Literal["verified", "failed", "inconclusive"]
RunStatus = Literal["verified", "completed", "failed", "inconclusive"]
ToolOutcome = Literal["completed", "failed", "denied"]


@dataclass
class VerificationResult:
    status: VerificationStatus
    evidence: str = ""
    reason: str = ""


@dataclass
class ToolTrace:
    call_id: str
    tool_name: str
    arguments: dict[str, Any]
    policy_allowed: bool = False
    policy_confirmation_required: bool = False
    policy_reason: str = ""
    started_at: float = field(default_factory=time.monotonic)
    completed_at: float | None = None
    outcome: ToolOutcome = "completed"
    result_preview: str = ""
    verification: VerificationResult | None = None


@dataclass
class RunTrace:
    run_id: str
    user_goal: str
    started_at: float = field(default_factory=time.monotonic)
    completed_at: float | None = None
    status: RunStatus = "completed"
    tool_traces: list[ToolTrace] = field(default_factory=list)
    output: str | None = None


class HarnessTrace:
    """Thread-safe collector owned by one agent instance."""

    def __init__(self, run_id: str, user_goal: str) -> None:
        self.run = RunTrace(run_id=run_id, user_goal=user_goal)
        self._lock = threading.Lock()

    @property
    def run_id(self) -> str:
        return self.run.run_id

    def start_tool(self, call_id: str, name: str, arguments: dict[str, Any]) -> ToolTrace:
        trace = ToolTrace(call_id=call_id, tool_name=name, arguments=dict(arguments))
        with self._lock:
            self.run.tool_traces.append(trace)
        return trace

    def policy(
        self, trace: ToolTrace, *, allowed: bool, confirmation_required: bool, reason: str
    ) -> None:
        with self._lock:
            trace.policy_allowed = allowed
            trace.policy_confirmation_required = confirmation_required
            trace.policy_reason = reason

    def finish_tool(
        self,
        trace: ToolTrace,
        *,
        outcome: ToolOutcome,
        result: Any = "",
        verification: VerificationResult | None = None,
    ) -> None:
        text = str(result)
        with self._lock:
            trace.completed_at = time.monotonic()
            trace.outcome = outcome
            trace.result_preview = text[:1000]
            trace.verification = verification

    def finish(self, *, status: RunStatus, output: Any = None) -> RunTrace:
        with self._lock:
            self.run.completed_at = time.monotonic()
            self.run.status = status
            self.run.output = None if output is None else str(output)
            return self.run


def derive_run_status(trace: RunTrace, *, has_output: bool = True) -> RunStatus:
    verifications = [t.verification for t in trace.tool_traces if t.verification is not None]
    if any(v.status == "failed" for v in verifications):
        return "failed"
    if any(v.status == "inconclusive" for v in verifications):
        return "inconclusive"
    if any(v.status == "verified" for v in verifications):
        return "verified"
    return "completed" if has_output else "inconclusive"


__all__ = ["HarnessTrace", "RunTrace", "ToolTrace", "VerificationResult", "derive_run_status"]


# Backwards-compatible alias used by some integrations.
TraceCollector = HarnessTrace


__all__.append("TraceCollector")


def new_run_trace(run_id: str, user_goal: str) -> RunTrace:
    return RunTrace(run_id=run_id, user_goal=user_goal)


__all__.append("new_run_trace")


def bounded_preview(value: Any, limit: int = 1000) -> str:
    return str(value)[:limit]


__all__.append("bounded_preview")


# Keep the public model useful without requiring a collector.
def now() -> float:
    return time.monotonic()


__all__.append("now")


# The verifier callback contract is intentionally structural.
Verifier = Any
__all__.append("Verifier")


# Explicitly expose literals for type-checking consumers.
__all__ += ["RunStatus", "ToolOutcome", "VerificationStatus"]


# Avoid mutable defaults in external construction while retaining dataclass ergonomics.
def make_verification(
    status: VerificationStatus, evidence: str = "", reason: str = ""
) -> VerificationResult:
    return VerificationResult(status=status, evidence=evidence[:1000], reason=reason[:1000])


__all__.append("make_verification")


# This is deliberately in-memory; persistence is out of scope for SPEC-001.
PERSISTENCE_ENABLED = False
__all__.append("PERSISTENCE_ENABLED")


# Public constant for consumers that need the evidence bound.
TRACE_PREVIEW_LIMIT = 1000
__all__.append("TRACE_PREVIEW_LIMIT")
