from nova.harness import HarnessTrace, VerificationResult, derive_run_status


def test_harness_records_tool_policy_result_and_verification():
    trace = HarnessTrace("run-1", "write a file")
    tool = trace.start_tool("call-1", "write_file", {"path": "/tmp/x"})
    trace.policy(tool, allowed=True, confirmation_required=False, reason="allowed")
    trace.finish_tool(
        tool,
        outcome="completed",
        result="Successfully wrote 1 lines",
        verification=VerificationResult("verified", "sha256=abc"),
    )
    result = trace.finish(status=derive_run_status(trace.run), output="done")
    assert result.run_id == "run-1"
    assert result.tool_traces[0].policy_allowed
    assert result.tool_traces[0].completed_at is not None
    assert result.status == "verified"


def test_harness_result_preview_redacts_textual_credentials():
    trace = HarnessTrace("run-secret", "inspect output")
    tool = trace.start_tool("call-secret", "http_client", {})
    trace.finish_tool(
        tool,
        outcome="completed",
        result="status=ok api_key=leaked-key Authorization: Bearer leaked-token",
    )

    assert tool.result_preview == ("status=ok api_key=[REDACTED] Authorization: Bearer [REDACTED]")
    assert "leaked-key" not in tool.result_preview
    assert "leaked-token" not in tool.result_preview


def test_harness_redacts_run_fields_and_tool_arguments():
    trace = HarnessTrace(
        "run-secret",
        "use api_key=goal-key password: goal-password Authorization: " + "Bearer goal-token",
    )
    tool = trace.start_tool(
        "call-secret",
        "http_client",
        {
            "api_key": "argument-key",
            "password": "argument-password",
            "headers": {"Authorization": "Bearer argument-token"},
        },
    )
    trace.finish_tool(
        tool,
        outcome="completed",
        result={"evidence": "password=preview-password Authorization: " + "Bearer preview-token"},
        verification=VerificationResult(
            "verified",
            "Authorization: " + "Bearer verification-token",
            "password=verification-password",
        ),
    )
    result = trace.finish(
        status="verified",
        output="api_key=output-key password: output-password Authorization: "
        + "Bearer output-token",
    )

    stored = str(result) + str(tool.arguments) + str(tool.verification)
    for secret in (
        "goal-key",
        "goal-password",
        "goal-token",
        "argument-key",
        "argument-password",
        "argument-token",
        "preview-password",
        "preview-token",
        "verification-token",
        "verification-password",
        "output-key",
        "output-password",
        "output-token",
    ):
        assert secret not in stored


def test_failed_verification_wins_over_successful_tool_result():
    trace = HarnessTrace("run-2", "patch")
    tool = trace.start_tool("call-2", "patch_file", {})
    trace.finish_tool(
        tool, outcome="completed", result="success", verification=VerificationResult("failed")
    )
    assert derive_run_status(trace.run) == "failed"


def test_inconclusive_interruption_is_not_completed():
    trace = HarnessTrace("run-3", "interrupt")
    tool = trace.start_tool("call-3", "write_file", {})
    trace.finish_tool(
        tool,
        outcome="failed",
        result="interrupted",
        verification=VerificationResult("inconclusive"),
    )
    assert derive_run_status(trace.run, has_output=False) == "inconclusive"


def test_later_verified_recovery_does_not_clear_failure():
    trace = HarnessTrace("run-4", "recover")
    first = trace.start_tool("call-1", "write_file", {})
    trace.finish_tool(first, outcome="failed", verification=VerificationResult("failed"))
    second = trace.start_tool("call-2", "write_file", {})
    trace.finish_tool(second, outcome="completed", verification=VerificationResult("verified"))

    assert derive_run_status(trace.run) == "failed"


def test_finish_does_not_clear_failed_status():
    trace = HarnessTrace("run-sticky", "retry")
    trace.finish(status="failed", output="failed")

    result = trace.finish(status="verified", output="recovered")

    assert result.status == "failed"


def test_inconclusive_after_failed_verification_does_not_clear_failure():
    trace = HarnessTrace("run-5", "retry")
    first = trace.start_tool("call-1", "write_file", {})
    trace.finish_tool(first, outcome="failed", verification=VerificationResult("failed"))
    second = trace.start_tool("call-2", "write_file", {})
    trace.finish_tool(second, outcome="failed", verification=VerificationResult("inconclusive"))

    assert derive_run_status(trace.run) == "failed"


def test_inconclusive_verification_can_recover_to_verified():
    trace = HarnessTrace("run-6", "retry")
    first = trace.start_tool("call-1", "write_file", {})
    trace.finish_tool(first, outcome="failed", verification=VerificationResult("inconclusive"))
    second = trace.start_tool("call-2", "write_file", {})
    trace.finish_tool(second, outcome="completed", verification=VerificationResult("verified"))

    assert derive_run_status(trace.run) == "verified"


def test_failure_after_verified_recovery_wins():
    trace = HarnessTrace("run-7", "retry")
    first = trace.start_tool("call-1", "write_file", {})
    trace.finish_tool(first, outcome="failed", verification=VerificationResult("failed"))
    second = trace.start_tool("call-2", "write_file", {})
    trace.finish_tool(second, outcome="completed", verification=VerificationResult("verified"))
    third = trace.start_tool("call-3", "write_file", {})
    trace.finish_tool(third, outcome="failed", verification=VerificationResult("failed"))

    assert derive_run_status(trace.run) == "failed"
