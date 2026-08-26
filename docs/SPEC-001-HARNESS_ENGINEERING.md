# Nova Agent Harness Engineering

**Status:** ✅ Active
**Last Updated:** August 2026
**Type:** SPEC (Technical Specification)
**Owner:** Eidolon Labs LLC

## 1. Goal

Add an explicit reliability layer around Nova's existing LLM/tool loop so that tool execution is observable, important side effects can be independently verified, and final responses distinguish verified completion from attempted or inconclusive work.

This specification deliberately extends Nova's current architecture. It does not introduce a workflow engine or a second agent loop. It permits optional Langfuse telemetry as the external observability sink; telemetry failure must never block the agent.

## 2. Design Mapping

| Harness capability | Nova implementation target | Status |
|---|---|---|
| User goal | `NovaAgent.run()` input and per-turn state | ✅ Existing |
| Context builder | `prompt.py`, `context.py`, wiki, skills, session history, budgets | ✅ Existing |
| LLM reasoning | `NovaAgent._call_llm()` and streaming loop | ✅ Existing |
| Policy gate | `PermissionChecker` before registry dispatch | ✅ Existing |
| Tools/runtime | Registry, tool handlers, workspace defaults, retries, read-only parallelism | ✅ Existing |
| Verification | Tool-specific postconditions and final acceptance state | ✅ Implemented |
| Accepted result | Structured completion status plus final response | ✅ Implemented |
| Observability | Unified in-memory run/tool traces exposed through existing hooks; optional Langfuse sink | ✅ Implemented (opt-in) |

## 3. Scope

### In scope

1. A per-run execution record with a stable run ID.
2. Structured tool-call traces containing policy, timing, outcome, and bounded evidence.
3. A verification result type with `verified`, `failed`, and `inconclusive` states.
4. Built-in postcondition verification for the safest high-value mutation paths:
   - `write_file`
   - `patch_file`
   - `git_*` operations that report success
5. An explicit final run status: `verified`, `completed`, `failed`, or `inconclusive`.
6. Tests proving the public agent path records and reports these states.
7. Documentation of the harness contract and residual limitations.

### Out of scope for this version

- A general planner or DAG/workflow engine.
- LLM-based verification as a substitute for executable checks.
- Automatic verification of arbitrary shell commands.
- Automatic read-back of arbitrary external API mutations.
- Persisting traces to a new database.
- Sending telemetry to Langfuse is specified below as an optional observability sink.
- Changing existing tool schemas or permission semantics.
- Treating a successful HTTP status alone as proof of a business-level mutation.

## 4. Terminology and State Model

### 4.1 Run status

A run status describes the strongest evidence available for the whole user turn:

- `verified`: at least one requested side effect had a verifier and all applicable verifiers passed; no applicable verifier failed.
- `completed`: the agent produced a final response and no verifier failed, but no applicable verifier established an executable postcondition.
- `failed`: a verifier or execution path definitively failed and the agent did not recover.
- `inconclusive`: execution ended with an applicable verifier unable to establish the postcondition, or the run was interrupted before acceptance.

A plain conversational answer with no side-effecting tool call may remain `completed`.

### 4.2 Verification status

Each verification returns:

```python
VerificationResult(
    status="verified" | "failed" | "inconclusive",
    evidence="bounded human-readable evidence",
    reason="optional failure or limitation explanation",
)
```

Verification must never expose secrets. Evidence is bounded by the existing tool-result budget and must not include authorization headers, API keys, or full secret-bearing file contents.

## 5. Proposed Components

### 5.1 `nova/harness.py`

Add small typed dataclasses and a run-scoped collector:

```python
@dataclass
class VerificationResult:
    status: Literal["verified", "failed", "inconclusive"]
    evidence: str = ""
    reason: str = ""


@dataclass
class ToolTrace:
    call_id: str
    tool_name: str
    arguments: dict[str, Any]
    policy_allowed: bool
    policy_confirmation_required: bool
    policy_reason: str
    started_at: float
    completed_at: float | None = None
    outcome: Literal["completed", "failed", "denied"] = "completed"
    result_preview: str = ""
    verification: VerificationResult | None = None


@dataclass
class RunTrace:
    run_id: str
    user_goal: str
    started_at: float
    completed_at: float | None = None
    status: Literal["verified", "completed", "failed", "inconclusive"] = "completed"
    tool_traces: list[ToolTrace] = field(default_factory=list)
```

The collector is in-memory and owned by `NovaAgent`. It is available for callbacks and tests, but is not persisted in this version.

### 5.2 Optional Langfuse telemetry sink

Add `langfuse>=3.0,<5` as an optional runtime dependency, installed by the project's observability extra. The integration uses the Langfuse Python SDK v3/v4 observation API (`get_client()` / `start_as_current_observation`) rather than hand-written HTTP calls.

Configuration is opt-in and layered with the existing config loader:

```yaml
observability:
  enabled: true
  provider: langfuse
  sample_rate: 1.0
  capture_input: false
  capture_output: false
  environment: production
  release: "2026.08"
  langfuse:
    public_key: "${LANGFUSE_PUBLIC_KEY}"
    secret_key: "${LANGFUSE_SECRET_KEY}"
    base_url: "${LANGFUSE_BASE_URL}"
    flush_at_shutdown: true
```

Required behavior:

- `observability.enabled` defaults to `false`; no credentials are required when disabled.
- Langfuse is initialized only when enabled, provider is `langfuse`, and both keys are available.
- `base_url` defaults to `https://cloud.langfuse.com` and supports self-hosted deployments.
- `sample_rate` is bounded to `0.0..1.0`; `0.0` sends nothing and `1.0` sends every run.
- Credentials may come from `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_BASE_URL`; secrets must not be logged or included in traces.
- Capture of user prompts, context, tool arguments, and final outputs defaults to `false`. When disabled, send metadata, names, statuses, timings, token counts, and bounded non-sensitive error classifications only.
- When enabled, telemetry is best-effort. SDK initialization, export, flush, or shutdown errors are logged locally and never change tool results or the agent's final answer.
- Create one root observation per run, child generation observations for LLM calls, and child span observations for policy/tool/verification operations. Include session ID, model, run ID, status, latency, retries, token usage, and cost where available.
- Flush on shutdown for CLI/short-lived processes; do not flush synchronously after every observation.

Langfuse's SDK is an adapter behind this contract. Core harness traces and tests must work with no Langfuse package installed, using a no-op client when the optional dependency or configuration is absent.

### 5.3 Registry-level verifier contract

Extend `ToolEntry` with an optional verifier callback. The callback receives the original arguments and tool result and returns `VerificationResult | None`.

- `None` means no executable verifier applies.
- Verifiers run only after a tool call returns.
- A verifier must be deterministic and side-effect free.
- A verifier failure must not be hidden by a successful tool return.

The registry remains responsible for dispatch; the agent remains responsible for policy and trace lifecycle.

### 5.3 Initial verifier set

#### `write_file`

Verify the target exists and its content matches the requested content. Use the existing file-operation implementation or a safe read-back helper, preserving encoding behavior. Evidence should contain path and a content hash or byte count, not the complete content.

#### `patch_file`

Verify the patch result indicates a replacement and read back the target to confirm the requested replacement is present and the old text is absent where the tool contract permits. If the patch reports no match, return `failed` rather than `inconclusive`.

#### `git_*`

Only verify operations for which the existing tool returns a checkable result. Do not claim repository state changed based solely on a generic success string. At minimum, preserve the raw tool outcome in the trace and return `None` for operations without a safe postcondition.

### 5.4 Trace lifecycle

The agent creates a `RunTrace` at the beginning of `run()` and closes it on every normal or interrupted exit path.

For every tool call:

1. Create a `ToolTrace` before permission evaluation.
2. Record the policy decision before confirmation.
3. Record start and completion timestamps using a monotonic clock.
4. Record only a bounded, secret-safe result preview.
5. Run the registered verifier after dispatch.
6. Set tool outcome and verification result.
7. Feed verifier failure/inconclusive information back into the conversation as the tool result or an adjacent structured message, so the LLM can recover or report accurately.

Existing lifecycle hooks remain compatible. The implementation may add trace fields to hook kwargs but must not remove existing fields.

## 6. Final Acceptance

At the end of a run, derive the run status from tool traces:

1. Any definitive verifier failure with no later successful recovery → `failed`.
2. Any applicable inconclusive verification with no later successful recovery → `inconclusive`.
3. At least one passed verification and no failures → `verified`.
4. Otherwise, if a final assistant response exists → `completed`.

The existing returned response remains a string for API compatibility. The structured status is exposed through `agent.last_run_trace` and lifecycle callbacks. The final response should include a concise status marker only when the status is not `completed`, to avoid changing ordinary conversational output unnecessarily.

## 7. Configuration

Verification is enabled for the built-in verifier set by default. Future configuration may disable selected verifiers, but disabling verification must not silently turn a failed verifier into a successful claim.

The optional Langfuse configuration is defined in section 5.2. It is disabled by default and must remain safe when the SDK is not installed or credentials are absent.

## 8. Security and Privacy

- Never store or log raw authorization headers, API keys, passwords, or credential-bearing arguments.
- Redact known secret-shaped values from trace argument copies and result previews.
- Bound previews to the existing tool-result budget; target 1,000 characters per trace.
- Keep traces in process memory only in this release.
- Verifiers must not follow arbitrary URLs, execute arbitrary commands, or mutate state.
- Permission denial is recorded as `denied` and is never represented as successful completion.

## 9. Compatibility

- Existing tool schemas and handler signatures remain valid.
- Existing `registry.register()` callers continue to work without a verifier argument.
- Existing hook consumers continue to receive their current required keyword arguments.
- Existing `NovaAgent.run()` return type remains `str`.
- Existing tests that call tool handlers directly remain valid.

## 10. Acceptance Criteria

- [ ] A run gets a stable ID and exposes `agent.last_run_trace` after completion.
- [ ] Every tool call records policy decision, timing, bounded result preview, and outcome.
- [ ] `write_file` and `patch_file` have executable postcondition verification with positive and negative tests.
- [ ] Verifier failures cannot produce a `verified` run status.
- [ ] Permission denials are traced without leaking sensitive arguments.
- [ ] Ordinary chat remains backward-compatible and returns a string.
- [ ] Existing full test suite, ruff, and mypy pass.
- [x] Documentation explains what is and is not verified.
- [x] Langfuse is an optional dependency and configuration is disabled by default.
- [x] Langfuse receives run, LLM, tool, policy, and verification telemetry when enabled.
- [x] Input/output capture is opt-in and disabled by default.
- [x] Langfuse export failures are isolated from agent execution.
- [x] Shutdown flush is covered by tests or a deterministic integration test seam.

## 11. Residual Gaps

This specification does not make arbitrary terminal commands, external API mutations, or natural-language claims independently verifiable. Those remain `completed` or `inconclusive` according to available evidence. A future extension can add explicit assertion arguments or tool-specific verifiers without changing the core trace and status model.

## Related Documentation

| Document | Relationship |
|---|---|
| [ADR-003 Tool System Review](ADR-003-TOOL_SYSTEM_REVIEW.md) | Existing tool architecture and previously identified observability gaps |
| [GUIDE-006 Hooks](GUIDE-006-HOOKS.md) | Existing lifecycle callback contract |
| [GUIDE-008 Permissions](GUIDE-008-PERMISSIONS.md) | Existing policy gate |
| [GUIDE-014 Retry and Error Handling](GUIDE-014-RETRY_AND_ERROR_HANDLING.md) | Existing execution recovery behavior |
| [Documentation Index](DOCUMENTATION_INDEX.md) | Documentation inventory |
