from app.rate_limit import SlidingWindowRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_limit_then_blocks() -> None:
    limiter = SlidingWindowRateLimiter(limit=2, clock=FakeClock())
    assert limiter.allow("1.1.1.1") is True
    assert limiter.allow("1.1.1.1") is True
    assert limiter.allow("1.1.1.1") is False


def test_clients_are_limited_separately() -> None:
    limiter = SlidingWindowRateLimiter(limit=1, clock=FakeClock())
    assert limiter.allow("1.1.1.1") is True
    assert limiter.allow("2.2.2.2") is True


def test_window_slides() -> None:
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, clock=clock)
    assert limiter.allow("1.1.1.1") is True
    clock.now += 59
    assert limiter.allow("1.1.1.1") is False
    clock.now += 1
    assert limiter.allow("1.1.1.1") is True


def test_blocked_requests_do_not_extend_the_window() -> None:
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, clock=clock)
    limiter.allow("1.1.1.1")
    clock.now += 30
    assert limiter.allow("1.1.1.1") is False
    clock.now += 30
    assert limiter.allow("1.1.1.1") is True


def test_inactive_clients_are_purged() -> None:
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, clock=clock)
    limiter.allow("1.1.1.1")
    limiter.allow("2.2.2.2")
    clock.now += 61
    limiter.allow("3.3.3.3")
    assert limiter.tracked_keys == 1
