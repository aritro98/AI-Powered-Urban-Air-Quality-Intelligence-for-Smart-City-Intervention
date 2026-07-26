"""
Simple thread-safe circuit breaker.

If a service fails repeatedly, stop actually attempting it for a cooldown
window and fail fast instead -- this is the real fix for a service that
is CONSISTENTLY (not intermittently) unreachable from a given network:
retrying it on every single zone, every single tab load, only adds the
full timeout cost every time for zero benefit. After the cooldown, we
automatically try again once in case the service has recovered.
"""
import threading
import time


class CircuitBreaker:
    def __init__(self, failure_threshold=2, cooldown_seconds=120):
        self._lock = threading.Lock()
        self._consecutive_failures = 0
        self._disabled_until = 0
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds

    def is_open(self):
        """True = circuit is OPEN (service currently assumed down, skip it)."""
        with self._lock:
            return time.time() < self._disabled_until

    def seconds_until_retry(self):
        with self._lock:
            return max(0, round(self._disabled_until - time.time()))

    def record_failure(self):
        with self._lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.failure_threshold:
                self._disabled_until = time.time() + self.cooldown_seconds

    def record_success(self):
        with self._lock:
            self._consecutive_failures = 0
            self._disabled_until = 0