"""Progress tracking and logging utilities."""

import logging
import sys
from pathlib import Path
from typing import Optional

from tqdm import tqdm


class ProgressLogger:
    """Handles progress tracking and logging.

    Combines a tqdm progress bar with Python logging for comprehensive
    progress reporting during scraping operations.

    Example:
        >>> with ProgressLogger(total=100, desc="Downloading") as progress:
        ...     for item in items:
        ...         result = download(item)
        ...         if result.success:
        ...             progress.log_success(item, "Downloaded")
        ...         else:
        ...             progress.log_failure(item, result.error)
    """

    def __init__(
        self,
        total: int,
        desc: str = "Progress",
        verbose: bool = False,
        log_file: Optional[Path] = None,
    ) -> None:
        """Initialize progress logger.

        Args:
            total: Total number of items to process
            desc: Description for progress bar
            verbose: Enable verbose logging
            log_file: Optional file to write logs to
        """
        self.total = total
        self.desc = desc
        self.verbose = verbose
        self.log_file = log_file

        # Setup logging
        self._logger = self._setup_logger()

        # Setup progress bar
        self._pbar = tqdm(
            total=total,
            desc=desc,
            unit="item",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
        )

        self.completed = 0
        self.failed = 0
        self.skipped = 0

    def _setup_logger(self) -> logging.Logger:
        """Setup logger with file and console handlers."""
        logger = logging.getLogger("webscraper")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        # Prevent duplicate handlers
        if logger.handlers:
            logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        console_format = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

        # File handler
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)

        return logger

    def update(self, n: int = 1) -> None:
        """Update progress bar.

        Args:
            n: Number of items to increment by
        """
        self._pbar.update(n)

    def log_success(self, item: str, message: str = "") -> None:
        """Log successful operation.

        Args:
            item: Item identifier (e.g., date)
            message: Optional additional message
        """
        self.completed += 1
        self.update()
        log_msg = f"[OK] {item}"
        if message:
            log_msg += f" - {message}"
        if self.verbose:
            self._logger.info(log_msg)

    def log_failure(self, item: str, error: str) -> None:
        """Log failed operation.

        Args:
            item: Item identifier
            error: Error message
        """
        self.failed += 1
        self.update()
        log_msg = f"[FAIL] {item} - ERROR: {error}"
        self._logger.error(log_msg)

    def log_skip(self, item: str, reason: str = "already completed") -> None:
        """Log skipped operation.

        Args:
            item: Item identifier
            reason: Reason for skipping
        """
        self.skipped += 1
        self.update()
        if self.verbose:
            self._logger.info(f"[SKIP] {item} - {reason}")

    def log_info(self, message: str) -> None:
        """Log info message.

        Args:
            message: Message to log
        """
        self._logger.info(message)

    def log_warning(self, message: str) -> None:
        """Log warning message.

        Args:
            message: Message to log
        """
        self._logger.warning(message)

    def log_debug(self, message: str) -> None:
        """Log debug message.

        Args:
            message: Message to log
        """
        if self.verbose:
            self._logger.debug(message)

    def set_description(self, desc: str) -> None:
        """Update progress bar description.

        Args:
            desc: New description
        """
        self._pbar.set_description(desc)

    def get_stats(self) -> dict[str, int]:
        """Get current statistics.

        Returns:
            Dictionary with completed, failed, skipped counts
        """
        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "remaining": self.total - self.completed - self.failed - self.skipped,
        }

    def print_summary(self) -> None:
        """Print final summary."""
        self._pbar.close()
        stats = self.get_stats()
        self._logger.info("")
        self._logger.info("=" * 60)
        self._logger.info("SCRAPING SUMMARY")
        self._logger.info("=" * 60)
        self._logger.info(f"Total items:     {stats['total']}")
        self._logger.info(f"Completed:       {stats['completed']}")
        self._logger.info(f"Failed:          {stats['failed']}")
        self._logger.info(f"Skipped:         {stats['skipped']}")
        success_rate = (
            (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
        )
        self._logger.info(f"Success rate:    {success_rate:.1f}%")
        self._logger.info("=" * 60)

    def close(self) -> None:
        """Close progress bar and handlers."""
        self._pbar.close()
        for handler in self._logger.handlers:
            handler.close()

    def __enter__(self) -> "ProgressLogger":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: object,
    ) -> None:
        """Context manager exit."""
        self.close()
