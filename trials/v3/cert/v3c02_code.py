"""token_bucket — a token-bucket rate limiter with an injected clock.

The clock is any zero-argument callable returning seconds as a number and
must be monotonic (never runs backwards), e.g. time.monotonic. All timing
flows through it, so tests drive the limiter with a fake clock and no real
waiting. The bucket starts full and refills continuously at `rate` tokens
per second, up to `capacity`. Safe for concurrent use from multiple
threads, provided the injected clock is itself safe to call concurrently.
"""
import threading


class TokenBucket:
    """Allow bursts up to `capacity`, sustained throughput of `rate`/sec."""

    def __init__(self, capacity, rate, clock):
        # `not (x > 0)` also rejects NaN, which `x <= 0` would let through.
        if not (capacity > 0):
            raise ValueError(f"capacity must be > 0, got {capacity!r}")
        if not (rate > 0):
            raise ValueError(f"rate must be > 0, got {rate!r}")
        if not callable(clock):
            raise TypeError("clock must be a zero-argument callable")
        self.capacity = float(capacity)
        self.rate = float(rate)
        self._clock = clock
        self._lock = threading.Lock()
        self._tokens = self.capacity
        self._last = clock()

    def _refill(self):
        # Caller must hold self._lock.
        now = self._clock()
        elapsed = now - self._last
        self._last = now
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)

    def _check_amount(self, tokens):
        if not (tokens > 0):  # also rejects NaN
            raise ValueError(f"tokens must be > 0, got {tokens!r}")
        if tokens > self.capacity:
            raise ValueError(
                f"requested {tokens!r} tokens but capacity is {self.capacity!r}"
            )

    def try_acquire(self, tokens=1):
        """Take `tokens` from the bucket if available; return True on success."""
        self._check_amount(tokens)
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def available(self):
        """Token count after refilling to now (float, capped at capacity)."""
        with self._lock:
            self._refill()
            return self._tokens

    def wait_time(self, tokens=1):
        """Seconds until `tokens` could be acquired; 0.0 if already possible.

        A prediction, not a reservation: other callers may drain the bucket
        in the meantime.
        """
        self._check_amount(tokens)
        with self._lock:
            self._refill()
            deficit = tokens - self._tokens
            if deficit <= 0:
                return 0.0
            return deficit / self.rate


if __name__ == "__main__":
    class _FakeClock:
        """Deterministic monotonic clock for the self-check."""

        def __init__(self):
            self.now = 0.0

        def __call__(self):
            return self.now

        def advance(self, seconds):
            self.now += seconds

    clock = _FakeClock()
    tb = TokenBucket(capacity=4, rate=2.0, clock=clock)

    assert tb.available() == 4.0            # starts full
    assert tb.try_acquire(4) is True        # boundary: spend exactly all
    assert tb.try_acquire(1) is False       # empty
    assert tb.wait_time(1) == 0.5           # deficit 1 at 2 tokens/sec
    clock.advance(0.25)                     # +0.5 tokens
    assert tb.try_acquire(1) is False       # 0.5 < 1
    assert tb.available() == 0.5
    clock.advance(0.25)                     # +0.5 tokens -> exactly 1.0
    assert tb.try_acquire(1) is True        # boundary: exactly enough
    assert tb.available() == 0.0
    clock.advance(1000.0)
    assert tb.available() == 4.0            # refill is capped at capacity
    assert tb.try_acquire(0.5) is True      # fractional amounts work
    assert tb.available() == 3.5
    assert tb.wait_time(2) == 0.0           # already affordable

    def expect_error(exc_type, fn):
        try:
            fn()
        except exc_type:
            return
        raise AssertionError(f"expected {exc_type.__name__}")

    expect_error(ValueError, lambda: tb.try_acquire(0))
    expect_error(ValueError, lambda: tb.try_acquire(-1))
    expect_error(ValueError, lambda: tb.try_acquire(float("nan")))
    expect_error(ValueError, lambda: tb.try_acquire(5))       # > capacity
    expect_error(ValueError, lambda: tb.wait_time(0))
    expect_error(ValueError, lambda: TokenBucket(0, 1.0, clock))
    expect_error(ValueError, lambda: TokenBucket(4, 0.0, clock))
    expect_error(ValueError, lambda: TokenBucket(float("nan"), 1.0, clock))
    expect_error(TypeError, lambda: TokenBucket(4, 1.0, clock=3.0))

    print("OK")
