"""HTTP API client with retry logic."""

import time
from pathlib import Path
from types import TracebackType
from typing import Any, Optional

import requests

from webscraper.exceptions import HttpClientError


class HttpClient:
    """HTTP client for making API requests with retry logic.

    Features:
    - Automatic retries with exponential backoff
    - Rate limit (429) handling with Retry-After header support
    - File download support
    - Session management for connection pooling

    Example:
        >>> with HttpClient("https://api.example.com") as client:
        ...     response = client.get("/data", params={"date": "2024-01-01"})
        ...     data = response.json()
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 60,
    ) -> None:
        """Initialize HTTP client.

        Args:
            base_url: Base URL for API requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._session = requests.Session()

    def set_headers(self, headers: dict[str, str]) -> None:
        """Set default headers for all requests.

        Args:
            headers: Dictionary of headers
        """
        self._session.headers.update(headers)

    def get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Make GET request with retry logic.

        Args:
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters
            **kwargs: Additional arguments for requests.get

        Returns:
            Response object

        Raises:
            HttpClientError: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self._request_with_retry("GET", url, params=params, **kwargs)

    def post(
        self,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Make POST request with retry logic.

        Args:
            endpoint: API endpoint
            data: Form data
            json: JSON data
            **kwargs: Additional arguments for requests.post

        Returns:
            Response object

        Raises:
            HttpClientError: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self._request_with_retry("POST", url, data=data, json=json, **kwargs)

    def download_file(
        self,
        endpoint: str,
        output_path: Path,
        params: Optional[dict[str, Any]] = None,
    ) -> Path:
        """Download file from API endpoint.

        Args:
            endpoint: API endpoint
            output_path: Path to save downloaded file
            params: Query parameters

        Returns:
            Path to downloaded file

        Raises:
            HttpClientError: If download fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self._request_with_retry(
            "GET", url, params=params, stream=True, timeout=self.timeout
        )

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        try:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return output_path
        except Exception as e:
            raise HttpClientError(f"Failed to write file {output_path}: {e}", cause=e)

    def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL
            **kwargs: Arguments for requests.request

        Returns:
            Response object

        Raises:
            HttpClientError: If request fails after retries
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                response = self._session.request(
                    method, url, timeout=kwargs.pop("timeout", self.timeout), **kwargs
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(
                        response.headers.get("Retry-After", str(self.retry_delay))
                    )
                    if attempt < self.max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    else:
                        raise HttpClientError(
                            f"Rate limited (429) after {self.max_retries} attempts"
                        )

                # Raise for other HTTP errors
                response.raise_for_status()
                return response

            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue

            except requests.exceptions.RequestException as e:
                last_exception = e
                # Don't retry on client errors (4xx except 429)
                if hasattr(e, "response") and e.response is not None:
                    if (
                        400 <= e.response.status_code < 500
                        and e.response.status_code != 429
                    ):
                        raise HttpClientError(f"Client error: {e}", cause=e)

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue

        # If we get here, all retries failed
        raise HttpClientError(
            f"Request failed after {self.max_retries} attempts: {last_exception}",
            cause=last_exception,
        )

    def close(self) -> None:
        """Close the session."""
        self._session.close()

    def __enter__(self) -> "HttpClient":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit."""
        self.close()
