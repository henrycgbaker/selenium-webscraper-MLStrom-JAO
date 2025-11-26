"""Rate limiting utilities."""
import time
import threading
from collections import deque
from datetime import datetime, timedelta


class RateLimiter:
    """Token bucket rate limiter for API requests."""

    def __init__(self, requests_per_minute: int = 60):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute  # seconds between requests
        self.request_times = deque(maxlen=requests_per_minute)
        self._lock = threading.Lock()

    def wait_if_needed(self):
        """Wait if necessary to respect rate limit."""
        with self._lock:
            now = time.time()

            # If we haven't hit the limit, just track the time
            if len(self.request_times) < self.requests_per_minute:
                self.request_times.append(now)
                return

            # Calculate time since oldest request
            oldest_request = self.request_times[0]
            time_since_oldest = now - oldest_request

            # If less than 60 seconds have passed, we need to wait
            if time_since_oldest < 60.0:
                wait_time = 60.0 - time_since_oldest
                time.sleep(wait_time)
                now = time.time()

            # Record this request
            self.request_times.append(now)

    def wait(self, seconds: float):
        """Wait for specified seconds.

        Args:
            seconds: Number of seconds to wait
        """
        time.sleep(seconds)

    def reset(self):
        """Reset the rate limiter."""
        with self._lock:
            self.request_times.clear()


class AdaptiveRateLimiter(RateLimiter):
    """Rate limiter that adapts to 429 responses."""

    def __init__(self, requests_per_minute: int = 60, backoff_factor: float = 2.0):
        """Initialize adaptive rate limiter.

        Args:
            requests_per_minute: Initial maximum requests per minute
            backoff_factor: Factor to reduce rate by when hitting 429
        """
        super().__init__(requests_per_minute)
        self.initial_rpm = requests_per_minute
        self.backoff_factor = backoff_factor
        self.consecutive_429s = 0

    def on_429_response(self, retry_after: int = 60):
        """Handle 429 Too Many Requests response.

        Args:
            retry_after: Seconds to wait (from Retry-After header)
        """
        with self._lock:
            self.consecutive_429s += 1

            # Reduce rate
            new_rpm = max(1, int(self.requests_per_minute / self.backoff_factor))
            self.requests_per_minute = new_rpm
            self.min_interval = 60.0 / new_rpm

            # Wait the specified time
            time.sleep(retry_after)

            # Clear recent requests
            self.request_times.clear()

    def on_success_response(self):
        """Handle successful response - gradually restore rate."""
        with self._lock:
            if self.consecutive_429s > 0:
                self.consecutive_429s = 0

                # Gradually increase rate back towards initial
                if self.requests_per_minute < self.initial_rpm:
                    new_rpm = min(
                        self.initial_rpm,
                        int(self.requests_per_minute * 1.1),  # 10% increase
                    )
                    self.requests_per_minute = new_rpm
                    self.min_interval = 60.0 / new_rpm
