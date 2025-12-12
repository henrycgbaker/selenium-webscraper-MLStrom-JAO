"""Centralized exception hierarchy for webscraper."""

from typing import Optional


class WebscraperError(Exception):
    """Base exception for all webscraper errors."""

    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.cause = cause


class ValidationError(WebscraperError):
    """Raised when data validation fails."""

    pass


class ClientError(WebscraperError):
    """Base exception for client-related errors."""

    pass


class HttpClientError(ClientError):
    """Raised when HTTP requests fail."""

    pass


class BrowserClientError(ClientError):
    """Raised when browser automation fails."""

    pass


class RateLimitError(WebscraperError):
    """Raised when rate limits are exceeded."""

    def __init__(
        self, message: str, retry_after: Optional[int] = None, cause: Optional[Exception] = None
    ) -> None:
        super().__init__(message, cause)
        self.retry_after = retry_after


class StateError(WebscraperError):
    """Raised when state management fails."""

    pass
