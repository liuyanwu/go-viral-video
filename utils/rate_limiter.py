"""
Rate limiter with random jitter for anti-detection.
"""

import asyncio
import random
import time
from typing import Optional


class RateLimiter:
    """
    Async rate limiter that mimics human request patterns.

    Features:
    - Configurable max requests per second
    - Random jitter (0~0.5s) added outside lock to avoid detection
    - Thread-safe via asyncio.Lock
    """

    def __init__(self, max_per_second: float = 2.0, jitter_range: float = 0.5):
        if max_per_second <= 0:
            max_per_second = 2.0
        self.max_per_second = max_per_second
        self.min_interval = 1.0 / max_per_second
        self.jitter_range = jitter_range
        self.last_request = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait until it's safe to make the next request."""
        async with self._lock:
            current = time.time()
            time_since_last = current - self.last_request

            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                await asyncio.sleep(wait_time)

            self.last_request = time.time()

        # Random jitter outside lock to mimic human behavior
        if self.jitter_range > 0:
            await asyncio.sleep(random.uniform(0, self.jitter_range))

    def acquire_sync(self):
        """Synchronous version for non-async contexts."""
        current = time.time()
        time_since_last = current - self.last_request

        if time_since_last < self.min_interval:
            time.sleep(self.min_interval - time_since_last)

        self.last_request = time.time()

        if self.jitter_range > 0:
            time.sleep(random.uniform(0, self.jitter_range))


class RetryHandler:
    """
    Exponential backoff retry handler.
    Backoff sequence: 1s, 2s, 5s (configurable).
    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff_sequence: Optional[list] = None,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.backoff_sequence = backoff_sequence or [1, 2, 5]
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Get delay for the given attempt number (0-indexed)."""
        idx = min(attempt, len(self.backoff_sequence) - 1)
        delay = self.backoff_sequence[idx]
        if self.jitter:
            delay += random.uniform(0, 1)
        return delay

    async def execute_async(self, func, *args, **kwargs):
        """
        Execute an async function with retry logic.

        Args:
            func: Async callable to execute.
            *args, **kwargs: Arguments to pass to func.

        Returns:
            Result of func.

        Raises:
            Last exception if all retries exhausted.
        """
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.get_delay(attempt)
                    await asyncio.sleep(delay)
        raise last_exception

    def execute_sync(self, func, *args, **kwargs):
        """Synchronous version of execute_async."""
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.get_delay(attempt)
                    time.sleep(delay)
        raise last_exception
