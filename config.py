"""Configuration management for web scraper framework."""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class ScraperConfig:
    """Configuration for a web scraper instance."""

    # Output settings
    output_dir: Path
    state_file: Optional[Path] = None

    # Rate limiting
    requests_per_minute: int = 60
    retry_delay: int = 60  # seconds to wait on 429 error
    max_retries: int = 3

    # Timeouts
    request_timeout: int = 30  # seconds
    selenium_page_load_timeout: int = 30  # seconds
    selenium_element_wait_timeout: int = 20  # seconds

    # Download settings
    download_timeout: int = 300  # seconds to wait for file download

    # Validation
    validate_downloads: bool = True
    min_file_size: int = 100  # minimum bytes for valid file

    # Logging
    verbose: bool = False
    log_file: Optional[Path] = None

    # Browser settings (for Selenium)
    headless: bool = True
    browser: str = "chrome"  # chrome, firefox, edge

    def __post_init__(self):
        """Ensure paths are Path objects."""
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        if self.state_file and isinstance(self.state_file, str):
            self.state_file = Path(self.state_file)
        if self.log_file and isinstance(self.log_file, str):
            self.log_file = Path(self.log_file)

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set default state file if not provided
        if not self.state_file:
            self.state_file = self.output_dir / "scraper_state.json"

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "output_dir": str(self.output_dir),
            "state_file": str(self.state_file) if self.state_file else None,
            "requests_per_minute": self.requests_per_minute,
            "retry_delay": self.retry_delay,
            "max_retries": self.max_retries,
            "request_timeout": self.request_timeout,
            "validate_downloads": self.validate_downloads,
            "min_file_size": self.min_file_size,
            "verbose": self.verbose,
            "headless": self.headless,
            "browser": self.browser,
        }
