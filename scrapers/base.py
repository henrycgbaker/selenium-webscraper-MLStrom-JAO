"""Base scraper abstract class."""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Optional
from dateutil.rrule import rrule, DAILY

from config import ScraperConfig
from utils.state import StateManager, DownloadStatus
from utils.progress import ProgressLogger
from utils.validation import CSVValidator
from core.rate_limiter import AdaptiveRateLimiter


class BaseScraper(ABC):
    """Abstract base class for web scrapers."""

    def __init__(self, config: ScraperConfig):
        """Initialize base scraper.

        Args:
            config: Scraper configuration
        """
        self.config = config
        self.state = StateManager(config.state_file)
        self.rate_limiter = AdaptiveRateLimiter(
            requests_per_minute=config.requests_per_minute
        )
        self.validator: Optional[CSVValidator] = None
        self.progress: Optional[ProgressLogger] = None

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
        pass

    @abstractmethod
    def get_validator(self) -> CSVValidator:
        """Get validator for downloaded files.

        This method must be implemented by subclasses.

        Returns:
            CSVValidator instance
        """
        pass

    def generate_date_range(self, start_date: date, end_date: date) -> List[date]:
        """Generate list of dates in range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of date objects
        """
        return list(rrule(DAILY, dtstart=start_date, until=end_date))

    def run(self, start_date: date, end_date: date, resume: bool = True):
        """Run the scraper for a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            resume: Whether to skip already completed dates
        """
        # Generate date range
        all_dates = self.generate_date_range(start_date, end_date)
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
        self.progress = ProgressLogger(
            total=len(pending_date_objects),
            desc="Downloading",
            verbose=self.config.verbose,
            log_file=self.config.log_file,
        )

        # Initialize validator
        self.validator = self.get_validator()

        # Log summary
        self.progress.log_info(f"Date range: {start_date} to {end_date}")
        self.progress.log_info(f"Total dates: {len(all_dates)}")
        if resume:
            completed = len(all_dates) - len(pending_date_objects)
            self.progress.log_info(f"Already completed: {completed}")
        self.progress.log_info(f"To download: {len(pending_date_objects)}")
        self.progress.log_info("")

        # Process each date
        for target_date in pending_date_objects:
            date_str = target_date.strftime("%Y-%m-%d")

            try:
                # Check if max attempts exceeded
                attempts = self.state.get_attempts(date_str)
                if attempts >= self.config.max_retries:
                    self.progress.log_skip(date_str, f"max attempts ({attempts}) exceeded")
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
                    self.progress.log_failure(date_str, "Download returned None")
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
                        self.progress.log_failure(date_str, f"Validation failed: {e}")
                        continue

                # Mark as completed
                self.state.set_status(
                    date_str, DownloadStatus.COMPLETED, file_path=str(file_path)
                )
                self.progress.log_success(date_str, f"→ {file_path.name}")
                self.rate_limiter.on_success_response()

            except Exception as e:
                error_msg = str(e)
                self.state.set_status(date_str, DownloadStatus.FAILED, error=error_msg)
                self.progress.log_failure(date_str, error_msg)

                # Handle rate limiting
                if "429" in error_msg or "rate limit" in error_msg.lower():
                    self.rate_limiter.on_429_response(self.config.retry_delay)

        # Print summary
        self.progress.print_summary()
        self.progress.close()

        # Print state summary
        summary = self.state.get_summary()
        print("\nState Summary:")
        print(f"  Total tracked: {summary['total']}")
        print(f"  Completed: {summary['completed']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Success rate: {summary['success_rate']:.1f}%")

    def cleanup(self):
        """Cleanup resources. Override in subclass if needed."""
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
