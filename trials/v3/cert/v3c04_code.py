"""retry_backoff — retry a callable with capped exponential backoff.

Fully simulated and deterministic: `sleep` receives each computed delay
(pass time.sleep in production, a recorder in tests) and a seeded `rng`
(random.Random) drives the jitter. Delay before the i-th retry (i >= 1):
    raw      = min(base_delay * 2 ** (i - 1), max_delay)
    jittered = raw * (1 + rng.uniform(-jitter_ratio, +jitter_ratio))
    delay    = min(jittered, max_delay)
max_delay is a hard ceiling even with positive jitter, and delays are
never negative because jitter_ratio < 1.
"""


def retry_call(fn, *, attempts, base_delay, max_delay, sleep,
               jitter_ratio=0.0, rng=None, retry_on=(Exception,)):
    """Call `fn()` up to `attempts` times; return its first result.

    Exceptions matching `retry_on` (an exception class or tuple of classes,
    as accepted by `except`) trigger a backoff sleep and another attempt;
    any other exception propagates immediately. A final-attempt failure
    with a matching exception is re-raised with no sleep after it.
    """
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1:
        raise ValueError(f"attempts must be an int >= 1, got {attempts!r}")
    # `not (x >= y)` also rejects NaN, which `x < y` would let through.
    if not (base_delay >= 0):
        raise ValueError(f"base_delay must be >= 0, got {base_delay!r}")
    if not (max_delay >= base_delay):
        raise ValueError(f"max_delay must be >= base_delay, got {max_delay!r}")
    if not 0.0 <= jitter_ratio < 1.0:
        raise ValueError(f"jitter_ratio must be in [0.0, 1.0), got {jitter_ratio!r}")
    if jitter_ratio > 0.0 and rng is None:
        raise ValueError("jitter_ratio > 0 requires an rng")

    ceiling = float(max_delay)
    raw = float(base_delay)
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except retry_on:
            if attempt == attempts:
                raise
            delay = raw
            if jitter_ratio > 0.0:
                delay = min(raw * (1.0 + rng.uniform(-jitter_ratio, jitter_ratio)), ceiling)
            sleep(delay)
            raw = min(raw * 2.0, ceiling)


if __name__ == "__main__":
    import random

    class _Flaky:
        """Raises ValueError for the first `failures` calls, then succeeds."""

        def __init__(self, failures, result="done"):
            self.failures = failures
            self.result = result
            self.calls = 0

        def __call__(self):
            self.calls += 1
            if self.calls <= self.failures:
                raise ValueError(f"simulated failure {self.calls}")
            return self.result

    def expect_raises(exc_type, fn):
        try:
            fn()
        except exc_type as exc:
            return exc
        raise AssertionError(f"expected {exc_type.__name__}")

    def run(failures, **kwargs):
        sleeps = []
        op = _Flaky(failures)
        return retry_call(op, sleep=sleeps.append, **kwargs), op, sleeps

    # Immediate success (no sleeps), then exact doubling after failures.
    result, op, sleeps = run(0, attempts=3, base_delay=1.0, max_delay=10.0)
    assert result == "done" and op.calls == 1 and sleeps == []
    result, op, sleeps = run(2, attempts=5, base_delay=1.0, max_delay=10.0)
    assert result == "done" and op.calls == 3 and sleeps == [1.0, 2.0]

    # max_delay caps the doubling; base_delay 0 gives zero-length sleeps.
    _, _, sleeps = run(4, attempts=5, base_delay=1.0, max_delay=3.0)
    assert sleeps == [1.0, 2.0, 3.0, 3.0]
    _, _, sleeps = run(2, attempts=3, base_delay=0.0, max_delay=5.0)
    assert sleeps == [0.0, 0.0]

    # Exhaustion: the last matching exception is re-raised, no final sleep.
    op, sleeps = _Flaky(10), []
    exc = expect_raises(ValueError, lambda: retry_call(
        op, attempts=3, base_delay=1.0, max_delay=10.0, sleep=sleeps.append))
    assert str(exc) == "simulated failure 3" and op.calls == 3 and sleeps == [1.0, 2.0]

    # attempts=1 boundary: a single call, failure re-raised, no sleeps.
    op, sleeps = _Flaky(1), []
    expect_raises(ValueError, lambda: retry_call(
        op, attempts=1, base_delay=1.0, max_delay=10.0, sleep=sleeps.append))
    assert op.calls == 1 and sleeps == []

    # Non-matching exceptions propagate immediately.
    calls, sleeps = [], []

    def not_retryable():
        calls.append(1)
        raise KeyError("nope")

    expect_raises(KeyError, lambda: retry_call(
        not_retryable, attempts=5, base_delay=1.0, max_delay=5.0,
        sleep=sleeps.append, retry_on=(ValueError,)))
    assert len(calls) == 1 and sleeps == []

    # Seeded jitter is deterministic and stays within bounds.
    def run_jittered(seed):
        _, op, sleeps = run(3, attempts=4, base_delay=1.0, max_delay=10.0,
                            jitter_ratio=0.5, rng=random.Random(seed))
        assert op.calls == 4
        return sleeps

    first = run_jittered(7)
    assert first == run_jittered(7) and len(first) == 3
    for raw, got in zip([1.0, 2.0, 4.0], first):
        assert raw * 0.5 <= got <= min(raw * 1.5, 10.0)

    def expect_bad_args(**overrides):
        kwargs = dict(attempts=3, base_delay=1.0, max_delay=5.0, sleep=lambda s: None)
        kwargs.update(overrides)
        expect_raises(ValueError, lambda: retry_call(_Flaky(0), **kwargs))

    expect_bad_args(attempts=0)
    expect_bad_args(attempts=True)           # bools are not counts
    expect_bad_args(base_delay=-1.0)
    expect_bad_args(base_delay=float("nan"))
    expect_bad_args(max_delay=0.5)           # below base_delay
    expect_bad_args(jitter_ratio=1.0)        # must be < 1
    expect_bad_args(jitter_ratio=0.3)        # jitter without rng

    print("OK")
