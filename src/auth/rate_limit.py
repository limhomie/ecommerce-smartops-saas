"""In-memory sliding-window rate limiter (token bucket)."""

from __future__ import annotations

import threading
import time

from src.observability.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Token-bucket rate limiter, keyed by user_id. Thread-safe."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, user_id: str) -> bool:
        """Return True if the request is allowed, False if rate limited."""
        now = time.time()
        cutoff = now - self._window

        with self._lock:
            bucket = self._buckets.get(user_id, [])
            # Remove expired entries
            bucket = [t for t in bucket if t > cutoff]
            if len(bucket) >= self._max:
                logger.warning("rate_limit_exceeded", user_id=user_id)
                return False
            bucket.append(now)
            self._buckets[user_id] = bucket
            return True

    def reset(self, user_id: str) -> None:
        with self._lock:
            self._buckets.pop(user_id, None)
