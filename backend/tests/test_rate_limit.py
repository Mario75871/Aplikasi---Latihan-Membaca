"""Test rate limiting in-memory (integrasi #4, D4)."""
from __future__ import annotations

from services.rate_limit import Limit, RateLimiter


def test_allows_up_to_limit_then_blocks():
    limiter = RateLimiter({"x": Limit(3, 60)})
    for _ in range(3):
        allowed, _ = limiter.check("k", "x", now=1000.0)
        assert allowed
    allowed, retry = limiter.check("k", "x", now=1000.0)
    assert not allowed
    assert retry >= 1


def test_window_expiry_frees_slot():
    limiter = RateLimiter({"x": Limit(1, 60)})
    assert limiter.check("k", "x", now=1000.0)[0]
    assert not limiter.check("k", "x", now=1010.0)[0]
    # Setelah jendela lewat > 60s → slot bebas.
    assert limiter.check("k", "x", now=1070.0)[0]


def test_separate_keys_are_independent():
    limiter = RateLimiter({"x": Limit(1, 60)})
    assert limiter.check("a", "x", now=0.0)[0]
    assert limiter.check("b", "x", now=0.0)[0]


def test_unknown_limit_is_unrestricted():
    limiter = RateLimiter({"x": Limit(1, 60)})
    assert limiter.check("k", "tidak-ada", now=0.0)[0]


def test_reset_clears_buckets():
    limiter = RateLimiter({"x": Limit(1, 60)})
    limiter.check("k", "x", now=0.0)
    limiter.reset()
    assert limiter.check("k", "x", now=0.0)[0]


def test_default_limits_match_decision_d4():
    from services.rate_limit import limits_from_env

    limits = limits_from_env()
    assert limits["audio_teacher"].max_requests == 10
    assert limits["audio_teacher"].window_sec == 600
    assert limits["audio_ip"].max_requests == 30
    assert limits["login_ip"].max_requests == 20
    assert limits["poll_teacher"].max_requests == 120
    assert limits["poll_teacher"].window_sec == 60
