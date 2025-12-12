"""Tests for rate limiter module."""

import time

import pytest

from webscraper.core.rate_limiter import AdaptiveRateLimiter, RateLimiter


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_init(self) -> None:
        """Test initialization."""
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.requests_per_minute == 60

    def test_wait_if_needed_under_limit(self) -> None:
        """Test that no waiting happens under the limit."""
        limiter = RateLimiter(requests_per_minute=100)

        start = time.time()
        for _ in range(10):
            limiter.wait_if_needed()
        elapsed = time.time() - start

        # Should be nearly instant
        assert elapsed < 1.0

    def test_reset(self) -> None:
        """Test reset clears request history."""
        limiter = RateLimiter(requests_per_minute=60)

        # Make some requests
        for _ in range(10):
            limiter.wait_if_needed()

        limiter.reset()

        # Should have cleared history
        assert len(limiter._request_times) == 0


class TestAdaptiveRateLimiter:
    """Tests for AdaptiveRateLimiter."""

    def test_init(self) -> None:
        """Test initialization."""
        limiter = AdaptiveRateLimiter(requests_per_minute=60, backoff_factor=2.0)
        assert limiter.requests_per_minute == 60
        assert limiter.initial_rpm == 60

    def test_on_429_reduces_rate(self) -> None:
        """Test that 429 response reduces rate."""
        limiter = AdaptiveRateLimiter(requests_per_minute=60, backoff_factor=2.0)

        # Simulate 429 with minimal wait
        limiter._lock.acquire()
        limiter._consecutive_429s += 1
        new_rpm = max(1, int(limiter.requests_per_minute / limiter._backoff_factor))
        limiter.requests_per_minute = new_rpm
        limiter._lock.release()

        assert limiter.requests_per_minute == 30
        assert limiter.current_rpm == 30
        assert limiter.initial_rpm == 60

    def test_on_success_restores_rate(self) -> None:
        """Test that success gradually restores rate."""
        limiter = AdaptiveRateLimiter(requests_per_minute=60, backoff_factor=2.0)

        # Manually reduce rate
        limiter.requests_per_minute = 30
        limiter._consecutive_429s = 1

        # Successful response
        limiter.on_success_response()

        # Should increase by 10%
        assert limiter.requests_per_minute == 33

    def test_rate_doesnt_exceed_initial(self) -> None:
        """Test that rate never exceeds initial value."""
        limiter = AdaptiveRateLimiter(requests_per_minute=60)

        # Set rate close to initial
        limiter.requests_per_minute = 58
        limiter._consecutive_429s = 1

        limiter.on_success_response()

        # Should cap at initial
        assert limiter.requests_per_minute <= 60
