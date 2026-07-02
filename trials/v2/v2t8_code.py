"""rate_window — a fixed-window request rate limiter with per-key counters.

Counts requests per key within aligned time windows. Not distributed: this
is a per-process limiter intended for single-instance services and tests.
"""
import threading
import time


class RateWindow:
    """Allow at most `limit` requests per `window_seconds` per key."""

    def __init__(self, limit, window_seconds):
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        if window_seconds <= 0:
            raise ValueError(f"window_seconds must be > 0, got {window_seconds}")
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._counters = {}  # key -> (window_start, count)

    def _current_window(self, now):
        return int(now // self.window_seconds) * self.window_seconds

    def allow(self, key, now=None):
        """Return True and count the request if `key` is under its limit."""
        if now is None:
            now = time.time()
        window = self._current_window(now)
        with self._lock:
            start, count = self._counters.get(key, (window, 0))
            if start != window:
                start, count = window, 0
            if count >= self.limit:
                self._counters[key] = (start, count)
                return False
            self._counters[key] = (start, count + 1)
            return True

    def remaining(self, key, now=None):
        """Requests left for `key` in the current window (no side effects)."""
        if now is None:
            now = time.time()
        window = self._current_window(now)
        with self._lock:
            start, count = self._counters.get(key, (window, 0))
            if start != window:
                return self.limit
            return max(0, self.limit - count)

    def reset(self, key=None):
        """Clear one key's counter, or all counters when key is None."""
        with self._lock:
            if key is None:
                self._counters.clear()
            else:
                self._counters.pop(key, None)


def demo():
    rw = RateWindow(limit=2, window_seconds=60)
    t0 = 1_000_000.0
    assert rw.allow("a", now=t0) is True
    assert rw.allow("a", now=t0 + 1) is True
    assert rw.allow("a", now=t0 + 2) is False
    assert rw.remaining("a", now=t0 + 2) == 0
    assert rw.allow("a", now=t0 + 61) is True   # new window
    assert rw.remaining("b", now=t0) == 2
    rw.reset()
    assert rw.remaining("a", now=t0 + 2) == 2
    print("rate_window demo: all assertions passed")


if __name__ == "__main__":
    demo()
