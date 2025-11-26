"""HTTP API client with retry logic."""
import requests
from typing import Optional, Dict, Any
from pathlib import Path
import time


class APIClientError(Exception):
    """Custom exception for API client errors."""

    pass


class APIClient:
    """HTTP client for making API requests with retry logic."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 60,
    ):
        """Initialize API client.

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
        self.session = requests.Session()

    def set_headers(self, headers: Dict[str, str]):
        """Set default headers for all requests.

        Args:
            headers: Dictionary of headers
        """
        self.session.headers.update(headers)

    def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs
    ) -> requests.Response:
        """Make GET request with retry logic.

        Args:
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters
            **kwargs: Additional arguments for requests.get

        Returns:
            Response object

        Raises:
            APIClientError: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self._request_with_retry("GET", url, params=params, **kwargs)

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs,
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
            APIClientError: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self._request_with_retry("POST", url, data=data, json=json, **kwargs)

    def download_file(
        self, endpoint: str, output_path: Path, params: Optional[Dict[str, Any]] = None
    ) -> Path:
        """Download file from API endpoint.

        Args:
            endpoint: API endpoint
            output_path: Path to save downloaded file
            params: Query parameters

        Returns:
            Path to downloaded file

        Raises:
            APIClientError: If download fails
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
            raise APIClientError(f"Failed to write file {output_path}: {e}")

    def _request_with_retry(
        self, method: str, url: str, **kwargs
    ) -> requests.Response:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL
            **kwargs: Arguments for requests.request

        Returns:
            Response object

        Raises:
            APIClientError: If request fails after retries
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method, url, timeout=self.timeout, **kwargs
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", self.retry_delay))
                    if attempt < self.max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    else:
                        raise APIClientError(
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
                    if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                        raise APIClientError(f"Client error: {e}")

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue

        # If we get here, all retries failed
        raise APIClientError(
            f"Request failed after {self.max_retries} attempts: {last_exception}"
        )

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
