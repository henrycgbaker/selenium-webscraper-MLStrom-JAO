"""Base scraper abstract class."""

from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path
from types import TracebackType
from typing import Optional

from webscraper.core.config import ScraperConfig
from webscraper.core.rate_limiter import AdaptiveRateLimiter
from webscraper.core.state import DownloadStatus, StateManager
from webscraper.utils.dates import generate_date_range
from webscraper.utils.progress import ProgressLogger
from webscraper.validation.csv import CSVValidator


class BaseScraper(ABC):
    """Abstract base class for web scrapers.

    Provides common functionality for date-based web scraping:
    - Date range iteration
    - State management for resume capability
    - Progress tracking
    - Rate limiting
    - Data validation hooks

    To create a custom scraper, inherit from this class and implement:
    - download_for_date(date) -> Path: Download logic for a single date
    - get_validator() -> CSVValidator: Return configured validator

    Example:
        >>> class MyScraper(BaseScraper):
        ...     def download_for_date(self, target_date: date) -> Optional[Path]:
        ...         # Implement download logic
        ...         return downloaded_file_path
        ...
        ...     def get_validator(self) -> CSVValidator:
        ...         return CSVValidator(min_file_size=100)
        ...
        >>> config = ScraperConfig(output_dir=Path("./data"))
        >>> with MyScraper(config) as scraper:
        ...     scraper.run(date(2024, 1, 1), date(2024, 1, 31))
    """

    def __init__(self, config: ScraperConfig) -> None:
        """Initialize base scraper.

        Args:
            config: Scraper configuration
        """
        self.config = config
        self._state: Optional[StateManager] = None
        self._rate_limiter: Optional[AdaptiveRateLimiter] = None
        self._validator: Optional[CSVValidator] = None
        self._progress: Optional[ProgressLogger] = None

    @property
    def state(self) -> StateManager:
        """Get state manager (lazy initialization)."""
        if self._state is None:
            if self.config.state_file is None:
                raise RuntimeError("State file not configured")
            self._state = StateManager(self.config.state_file)
        return self._state

    @property
    def rate_limiter(self) -> AdaptiveRateLimiter:
        """Get rate limiter (lazy initialization)."""
        if self._rate_limiter is None:
            self._rate_limiter = AdaptiveRateLimiter(
                requests_per_minute=self.config.requests_per_minute
            )
        return self._rate_limiter

    @property
    def validator(self) -> CSVValidator:
        """Get validator (lazy initialization)."""
        if self._validator is None:
            self._validator = self.get_validator()
        return self._validator

    @property
    def progress(self) -> Optional[ProgressLogger]:
        """Get progress logger (may be None if not in run())."""
        return self._progress

    @abstractmethod
    def download_for_date(self, target_date: date) -> Optional[Path]:
        """Download data for a specific date.

        This method must be implemented by subclasses.

        Args:
            target_date: Date to download data for

        Returns:
            Path to downloaded file, or None if failed

        Raises:
            Exception: If download fails
        """
        ...

    @abstractmethod
    def get_validator(self) -> CSVValidator:
        """Get validator for downloaded files.

        This method must be implemented by subclasses.

        Returns:
            CSVValidator instance
        """
        ...

    def run(
        self,
        start_date: date,
        end_date: date,
        resume: bool = True,
    ) -> None:
        """Run the scraper for a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            resume: Whether to skip already completed dates
        """
        # Generate date range
        all_dates = generate_date_range(start_date, end_date)
        date_strings = [d.strftime("%Y-%m-%d") for d in all_dates]

        # Filter out completed dates if resuming
        if resume:
            pending_dates = self.state.get_pending_dates(date_strings)
            pending_date_objects = [
                datetime.strptime(d, "%Y-%m-%d").date() for d in pending_dates
            ]
        else:
            pending_date_objects = all_dates

        # Initialize progress logger
        self._progress = ProgressLogger(
            total=len(pending_date_objects),
            desc="Downloading",
            verbose=self.config.verbose,
            log_file=self.config.log_file,
        )

        # Log summary
        self._progress.log_info(f"Date range: {start_date} to {end_date}")
        self._progress.log_info(f"Total dates: {len(all_dates)}")
        if resume:
            completed = len(all_dates) - len(pending_date_objects)
            self._progress.log_info(f"Already completed: {completed}")
        self._progress.log_info(f"To download: {len(pending_date_objects)}")
        self._progress.log_info("")

        # Process each date
        for target_date in pending_date_objects:
            date_str = target_date.strftime("%Y-%m-%d")

            try:
                # Check if max attempts exceeded
                attempts = self.state.get_attempts(date_str)
                if attempts >= self.config.max_retries:
                    self._progress.log_skip(
                        date_str, f"max attempts ({attempts}) exceeded"
                    )
                    continue

                # Mark as in progress
                self.state.set_status(date_str, DownloadStatus.IN_PROGRESS)

                # Apply rate limiting
                self.rate_limiter.wait_if_needed()

                # Download
                file_path = self.download_for_date(target_date)

                if file_path is None:
                    self.state.set_status(
                        date_str, DownloadStatus.FAILED, error="Download returned None"
                    )
                    self._progress.log_failure(date_str, "Download returned None")
                    self.rate_limiter.on_success_response()
                    continue

                # Validate if enabled
                if self.config.validate_downloads:
                    try:
                        self.validator.validate_file(file_path)
                    except Exception as e:
                        self.state.set_status(
                            date_str,
                            DownloadStatus.FAILED,
                            file_path=str(file_path),
                            error=f"Validation failed: {e}",
                        )
                        self._progress.log_failure(date_str, f"Validation failed: {e}")
                        continue

                # Mark as completed
                self.state.set_status(
                    date_str, DownloadStatus.COMPLETED, file_path=str(file_path)
                )
                self._progress.log_success(date_str, f"-> {file_path.name}")
                self.rate_limiter.on_success_response()

            except Exception as e:
                error_msg = str(e)
                self.state.set_status(date_str, DownloadStatus.FAILED, error=error_msg)
                self._progress.log_failure(date_str, error_msg)

                # Handle rate limiting
                if "429" in error_msg or "rate limit" in error_msg.lower():
                    self.rate_limiter.on_429_response(self.config.retry_delay)

        # Print summary
        self._progress.print_summary()
        self._progress.close()

        # Print state summary
        summary = self.state.get_summary()
        print("\nState Summary:")
        print(f"  Total tracked: {summary['total']}")
        print(f"  Completed: {summary['completed']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Success rate: {summary['success_rate']:.1f}%")

    def cleanup(self) -> None:
        """Cleanup resources. Override in subclass if needed."""
        pass

    def __enter__(self) -> "BaseScraper":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit."""
        self.cleanup()
