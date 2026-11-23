import pytest
from starlette.requests import Request

from app.rate_limit import SlidingWindowRateLimiter, get_client_key


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


def make_request(*forwarded: str) -> Request:
    headers = [(b"x-forwarded-for", value.encode()) for value in forwarded]
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/classify",
            "headers": headers,
            "client": ("10.0.0.5", 4321),
        }
    )


def test_client_key_ignores_forwarded_header_by_default() -> None:
    assert get_client_key(make_request("9.9.9.9"), trust_proxy=False) == "10.0.0.5"


@pytest.mark.parametrize(
    ("forwarded", "expected"),
    [
        (("9.9.9.9",), "9.9.9.9"),
        (("1.1.1.1, 9.9.9.9",), "9.9.9.9"),
        (("1.1.1.1", "2.2.2.2, 9.9.9.9"), "9.9.9.9"),
        (("9.9.9.9:51234",), "9.9.9.9"),
        (("2001:db8::1",), "2001:db8::1"),
        (("[2001:db8::1]:51234",), "2001:db8::1"),
    ],
)
def test_client_key_uses_rightmost_proxy_entry(forwarded: tuple[str, ...], expected: str) -> None:
    assert get_client_key(make_request(*forwarded), trust_proxy=True) == expected


@pytest.mark.parametrize("forwarded", [(), ("",), ("1.1.1.1, ",)])
def test_client_key_falls_back_to_peer_address(forwarded: tuple[str, ...]) -> None:
    assert get_client_key(make_request(*forwarded), trust_proxy=True) == "10.0.0.5"
