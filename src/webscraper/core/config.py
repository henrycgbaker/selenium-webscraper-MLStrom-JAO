"""Configuration management using Pydantic."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ScraperConfig(BaseModel):
    """Configuration for a web scraper instance.

    Attributes:
        output_dir: Directory to save downloaded files
        state_file: Path to state file for resume capability (auto-generated if None)
        requests_per_minute: Maximum requests per minute for rate limiting
        retry_delay: Seconds to wait before retrying after errors
        max_retries: Maximum retry attempts per item
        request_timeout: HTTP request timeout in seconds
        download_timeout: File download timeout in seconds
        validate_downloads: Whether to validate downloaded files
        min_file_size: Minimum valid file size in bytes
        verbose: Enable verbose logging
        log_file: Optional path to log file
        headless: Run browser in headless mode
        browser: Browser to use for Selenium (chrome, firefox)
        selenium_page_load_timeout: Page load timeout for Selenium
        selenium_element_wait_timeout: Element wait timeout for Selenium
    """

    output_dir: Path
    state_file: Optional[Path] = None

    # Rate limiting
    requests_per_minute: int = Field(default=60, ge=1, le=1000)
    retry_delay: int = Field(default=60, ge=1)
    max_retries: int = Field(default=3, ge=1, le=10)

    # Timeouts
    request_timeout: int = Field(default=30, ge=1)
    download_timeout: int = Field(default=300, ge=1)
    selenium_page_load_timeout: int = Field(default=30, ge=1)
    selenium_element_wait_timeout: int = Field(default=20, ge=1)

    # Validation
    validate_downloads: bool = True
    min_file_size: int = Field(default=100, ge=0)

    # Logging
    verbose: bool = False
    log_file: Optional[Path] = None

    # Browser settings
    headless: bool = True
    browser: str = Field(default="chrome", pattern="^(chrome|firefox)$")

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("output_dir", "state_file", "log_file", mode="before")
    @classmethod
    def convert_to_path(cls, v: Optional[str | Path]) -> Optional[Path]:
        """Convert string paths to Path objects."""
        if v is None:
            return None
        return Path(v) if isinstance(v, str) else v

    @model_validator(mode="after")
    def setup_defaults(self) -> "ScraperConfig":
        """Set up default values and create directories."""
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set default state file if not provided
        if self.state_file is None:
            self.state_file = self.output_dir / "scraper_state.json"

        # Create log file directory if specified
        if self.log_file is not None:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

        return self

    def to_dict(self) -> dict[str, object]:
        """Convert config to dictionary."""
        return {
            "output_dir": str(self.output_dir),
            "state_file": str(self.state_file) if self.state_file else None,
            "requests_per_minute": self.requests_per_minute,
            "retry_delay": self.retry_delay,
            "max_retries": self.max_retries,
            "request_timeout": self.request_timeout,
            "download_timeout": self.download_timeout,
            "validate_downloads": self.validate_downloads,
            "min_file_size": self.min_file_size,
            "verbose": self.verbose,
            "headless": self.headless,
            "browser": self.browser,
        }
