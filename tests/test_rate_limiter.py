"""
Test suite for rate limiter module.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.rate_limiter import RateLimiter, RetryHandler


def test_rate_limiter_sync():
    limiter = RateLimiter(max_per_second=10.0, jitter_range=0)
    start = time.time()
    for _ in range(5):
        limiter.acquire_sync()
    elapsed = time.time() - start
    assert elapsed >= 0.4


def test_rate_limiter_with_jitter():
    limiter = RateLimiter(max_per_second=100.0, jitter_range=0.1)
    start = time.time()
    limiter.acquire_sync()
    elapsed = time.time() - start
    assert elapsed >= 0


def test_retry_handler_success():
    handler = RetryHandler(max_retries=3, backoff_sequence=[0.01, 0.01, 0.01], jitter=False)
    call_count = 0

    def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary error")
        return "success"

    result = handler.execute_sync(flaky_func)
    assert result == "success"
    assert call_count == 3


def test_retry_handler_exhausted():
    handler = RetryHandler(max_retries=2, backoff_sequence=[0.01, 0.01], jitter=False)

    def always_fail():
        raise ValueError("Permanent error")

    try:
        handler.execute_sync(always_fail)
        assert False, "Should have raised"
    except ValueError as e:
        assert str(e) == "Permanent error"
