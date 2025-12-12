"""Protocol definitions for client interfaces."""

from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class Client(Protocol):
    """Base protocol for all clients."""

    def close(self) -> None:
        """Close the client and release resources."""
        ...

    def __enter__(self) -> "Client":
        """Context manager entry."""
        ...

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> None:
        """Context manager exit."""
        ...


@runtime_checkable
class HttpClientProtocol(Client, Protocol):
    """Protocol for HTTP clients."""

    def get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """Make GET request."""
        ...

    def post(
        self,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """Make POST request."""
        ...

    def download_file(
        self,
        endpoint: str,
        output_path: Path,
        params: Optional[dict[str, Any]] = None,
    ) -> Path:
        """Download file from endpoint."""
        ...


@runtime_checkable
class BrowserClientProtocol(Client, Protocol):
    """Protocol for browser automation clients."""

    def start(self) -> None:
        """Start the browser."""
        ...

    def navigate(self, url: str) -> None:
        """Navigate to URL."""
        ...

    def click(self, selector: str) -> None:
        """Click an element."""
        ...

    def wait_for_download(
        self,
        timeout: int = 60,
        existing_files: Optional[set[Path]] = None,
    ) -> Optional[Path]:
        """Wait for a file download to complete."""
        ...

    def quit(self) -> None:
        """Close the browser."""
        ...
