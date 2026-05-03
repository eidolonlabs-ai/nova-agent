"""Retry logic with exponential backoff for API calls.

Handles transient errors (rate limits, server errors, timeouts)
with configurable retry counts, backoff multipliers, and
error classification.
"""

import logging
import random
import time
from typing import Any

logger = logging.getLogger(__name__)


# Error classifications
class ErrorType:
    RETRYABLE = "retryable"       # Transient — should retry
    NON_RETRYABLE = "non_retryable"  # Permanent — should not retry
    CONTEXT_OVERFLOW = "overflow"    # Context too long — needs compression


# HTTP status codes that are retryable
_RETRYABLE_STATUS = {429, 500, 502, 503, 504, 529}

# Error message patterns that indicate retryable errors
_RETRYABLE_PATTERNS = [
    "rate limit",
    "too many requests",
    "server error",
    "internal error",
    "bad gateway",
    "service unavailable",
    "gateway timeout",
    "upstream error",
    "connection reset",
    "connection refused",
    "timeout",
    "temporary failure",
]

# Error patterns that indicate context overflow
_OVERFLOW_PATTERNS = [
    "context length",
    "context window",
    "token limit",
    "maximum context",
    "prompt is too long",
    "input length",
    "exceeds the maximum",
]


def classify_error(status_code: int | None = None, message: str = "") -> str:
    """Classify an error as retryable, non-retryable, or context overflow.

    Args:
        status_code: HTTP status code (if available).
        message: Error message text.

    Returns:
        One of ErrorType.RETRYABLE, ErrorType.NON_RETRYABLE, ErrorType.CONTEXT_OVERFLOW.
    """
    text = (message or "").lower()

    # Check for context overflow first (highest priority)
    for pattern in _OVERFLOW_PATTERNS:
        if pattern in text:
            return ErrorType.CONTEXT_OVERFLOW

    # Check retryable status codes
    if status_code in _RETRYABLE_STATUS:
        return ErrorType.RETRYABLE

    # Check retryable error patterns
    for pattern in _RETRYABLE_PATTERNS:
        if pattern in text:
            return ErrorType.RETRYABLE

    # 4xx errors (except 429) are generally non-retryable
    if status_code and 400 <= status_code < 500:
        return ErrorType.NON_RETRYABLE

    # 5xx server errors are retryable
    if status_code and 500 <= status_code < 600:
        return ErrorType.RETRYABLE

    # No status code — unknown error, retryable (safer)
    if status_code is None:
        return ErrorType.RETRYABLE

    # Default: non-retryable for known non-retryable status codes
    return ErrorType.NON_RETRYABLE


def retry_with_backoff(
    func,
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    jitter: bool = True,
    **kwargs: Any,
) -> Any:
    """Call a function with exponential backoff retry.

    Args:
        func: Function to call. Should raise an exception on failure.
        *args: Positional arguments for the function.
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay in seconds.
        backoff_multiplier: Multiplier for each retry.
        jitter: Add random jitter to prevent thundering herd.
        **kwargs: Keyword arguments for the function.

    Returns:
        The return value of the function.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            error_msg = str(e)
            # httpx.HTTPStatusError stores status_code on .response
            status_code = getattr(e, "status_code", None)
            if status_code is None:
                response = getattr(e, "response", None)
                if response is not None:
                    status_code = getattr(response, "status_code", None)
            error_type = classify_error(status_code, error_msg)

            # Don't retry context overflow errors
            if error_type == ErrorType.CONTEXT_OVERFLOW:
                raise

            # Don't retry non-retryable errors
            if error_type == ErrorType.NON_RETRYABLE:
                raise

            if attempt < max_retries:
                delay = min(base_delay * (backoff_multiplier ** attempt), max_delay)
                if jitter:
                    delay *= (0.5 + random.random() * 0.5)  # 50%-150% of delay

                logger.warning(
                    "API call failed (attempt %d/%d, %s): %s — retrying in %.1fs",
                    attempt + 1, max_retries, error_type, error_msg[:200], delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "API call failed after %d retries (%s): %s",
                    max_retries, error_type, error_msg[:200],
                )

    raise last_exception  # type: ignore[misc]


def retry_api_call(
    http_client,
    method: str,
    url: str,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs: Any,
) -> Any:
    """Make an HTTP request with retry logic.

    Convenience wrapper around retry_with_backoff for httpx calls.

    Args:
        http_client: httpx.Client instance.
        method: HTTP method ("GET", "POST", etc.).
        url: URL to request.
        max_retries: Maximum retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay in seconds.
        **kwargs: Additional arguments passed to httpx request.

    Returns:
        httpx.Response object.
    """
    def _do_request() -> Any:
        response = getattr(http_client, method.lower())(url, **kwargs)
        response.raise_for_status()
        return response

    return retry_with_backoff(
        _do_request,
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
    )
