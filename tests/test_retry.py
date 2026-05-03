"""Tests for the retry logic."""

import contextlib
from unittest.mock import MagicMock, patch

import httpx

from nova.retry import (
    _OVERFLOW_PATTERNS,
    _RETRYABLE_PATTERNS,
    _RETRYABLE_STATUS,
    ErrorType,
    classify_error,
    retry_api_call,
    retry_with_backoff,
)

# ── classify_error ──────────────────────────────────────────────────────────


def test_classify_context_overflow():
    for pattern in _OVERFLOW_PATTERNS:
        assert classify_error(message=pattern) == ErrorType.CONTEXT_OVERFLOW


def test_classify_retryable_status():
    for status in _RETRYABLE_STATUS:
        assert classify_error(status_code=status) == ErrorType.RETRYABLE


def test_classify_retryable_patterns():
    for pattern in _RETRYABLE_PATTERNS:
        assert classify_error(message=pattern) == ErrorType.RETRYABLE


def test_classify_non_retryable_4xx():
    for status in [400, 401, 403, 404, 405, 409, 422]:
        assert classify_error(status_code=status) == ErrorType.NON_RETRYABLE


def test_classify_429_is_retryable():
    assert classify_error(status_code=429) == ErrorType.RETRYABLE


def test_classify_unknown_is_retryable():
    assert classify_error() == ErrorType.RETRYABLE


def test_classify_overflow_takes_priority():
    # Even with a retryable status code, overflow should win
    assert classify_error(status_code=500, message="context length exceeded") == ErrorType.CONTEXT_OVERFLOW


# ── retry_with_backoff ──────────────────────────────────────────────────────


def test_retry_succeeds_first_try():
    call_count = 0

    def success():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = retry_with_backoff(success, max_retries=3)
    assert result == "ok"
    assert call_count == 1


def test_retry_succeeds_after_failures():
    call_count = 0

    def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.HTTPStatusError(
                "rate limit",
                request=MagicMock(),
                response=MagicMock(status_code=429),
            )
        return "ok"

    result = retry_with_backoff(flaky, max_retries=3, base_delay=0.01)
    assert result == "ok"
    assert call_count == 3


def test_retry_exhausts():
    call_count = 0

    def always_fails():
        nonlocal call_count
        call_count += 1
        raise httpx.HTTPStatusError(
            "server error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

    with contextlib.suppress(httpx.HTTPStatusError):
        retry_with_backoff(always_fails, max_retries=2, base_delay=0.01)

    assert call_count == 3  # 1 initial + 2 retries


def test_retry_non_retryable_raises_immediately():
    call_count = 0

    def bad_request():
        nonlocal call_count
        call_count += 1
        raise httpx.HTTPStatusError(
            "bad request",
            request=MagicMock(),
            response=MagicMock(status_code=400),
        )

    with contextlib.suppress(httpx.HTTPStatusError):
        retry_with_backoff(bad_request, max_retries=3, base_delay=0.01)

    # Non-retryable errors should not retry (but first attempt always runs)
    assert call_count == 1


def test_retry_context_overflow_raises_immediately():
    call_count = 0

    def overflow():
        nonlocal call_count
        call_count += 1
        raise httpx.HTTPStatusError(
            "context length exceeded",
            request=MagicMock(),
            response=MagicMock(status_code=400),
        )

    with contextlib.suppress(httpx.HTTPStatusError):
        retry_with_backoff(overflow, max_retries=3, base_delay=0.01)

    assert call_count == 1


def test_retry_with_jitter():
    """Test that jitter adds randomness to delays."""
    delays = []

    def failing():
        raise ValueError("test")

    with (
        patch("nova.retry.time.sleep", lambda d: delays.append(d)),
        contextlib.suppress(ValueError),
    ):
        retry_with_backoff(failing, max_retries=3, base_delay=1.0, jitter=True)

    # With jitter, delays should vary (not all identical)
    assert len(delays) == 3
    # Delays follow: base_delay * (backoff_multiplier ** attempt) * jitter(0.5-1.5)
    # Attempt 0: 1.0 * 0.5-1.5 = 0.5-1.5
    # Attempt 1: 2.0 * 0.5-1.5 = 1.0-3.0
    # Attempt 2: 4.0 * 0.5-1.5 = 2.0-6.0
    assert 0.5 <= delays[0] <= 1.5
    assert 1.0 <= delays[1] <= 3.0
    assert 2.0 <= delays[2] <= 6.0


def test_retry_without_jitter():
    """Test that delays are deterministic without jitter."""
    delays = []

    def failing():
        raise ValueError("test")

    with (
        patch("nova.retry.time.sleep", lambda d: delays.append(d)),
        contextlib.suppress(ValueError),
    ):
        retry_with_backoff(failing, max_retries=3, base_delay=1.0, jitter=False)

    assert len(delays) == 3
    # Without jitter, delays should be exact: 1.0, 2.0, 4.0
    assert delays[0] == 1.0
    assert delays[1] == 2.0
    assert delays[2] == 4.0


def test_retry_max_delay_cap():
    """Test that delays don't exceed max_delay."""
    delays = []

    def failing():
        raise ValueError("test")

    with (
        patch("nova.retry.time.sleep", lambda d: delays.append(d)),
        contextlib.suppress(ValueError),
    ):
        retry_with_backoff(
            failing, max_retries=5, base_delay=1.0, max_delay=3.0, jitter=False,
        )

    # All delays should be capped at 3.0
    for d in delays:
        assert d <= 3.0


# ── retry_api_call ──────────────────────────────────────────────────────────


def test_retry_api_call_success():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ok"}
    mock_client.post.return_value = mock_response

    result = retry_api_call(mock_client, "POST", "/test", json={"data": "test"})
    assert result.json() == {"status": "ok"}


def test_retry_api_call_with_retries():
    mock_client = MagicMock()
    mock_response_ok = MagicMock()
    mock_response_ok.json.return_value = {"status": "ok"}

    mock_response_err = MagicMock()
    mock_response_err.status_code = 429
    mock_response_err.text = "rate limit"

    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] < 3:
            err = MagicMock(status_code=429)
            err.text = "rate limit"
            raise httpx.HTTPStatusError("rate limit", request=MagicMock(), response=err)
        return mock_response_ok

    mock_client.post.side_effect = side_effect

    result = retry_api_call(
        mock_client, "POST", "/test",
        json={"data": "test"},
        max_retries=3,
        base_delay=0.01,
    )
    assert result.json() == {"status": "ok"}
    assert call_count[0] == 3
