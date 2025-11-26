"""Progress tracking and logging utilities."""
import sys
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime
from tqdm import tqdm


class ProgressLogger:
    """Handles progress tracking and logging."""

    def __init__(
        self,
        total: int,
        desc: str = "Progress",
        verbose: bool = False,
        log_file: Optional[Path] = None,
    ):
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
        self.logger = self._setup_logger()

        # Setup progress bar
        self.pbar = tqdm(
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

    def update(self, n: int = 1):
        """Update progress bar.

        Args:
            n: Number of items to increment by
        """
        self.pbar.update(n)

    def log_success(self, item: str, message: str = ""):
        """Log successful operation.

        Args:
            item: Item identifier (e.g., date)
            message: Optional additional message
        """
        self.completed += 1
        self.update()
        log_msg = f"✓ {item}"
        if message:
            log_msg += f" - {message}"
        if self.verbose:
            self.logger.info(log_msg)

    def log_failure(self, item: str, error: str):
        """Log failed operation.

        Args:
            item: Item identifier
            error: Error message
        """
        self.failed += 1
        self.update()
        log_msg = f"✗ {item} - ERROR: {error}"
        self.logger.error(log_msg)

    def log_skip(self, item: str, reason: str = "already completed"):
        """Log skipped operation.

        Args:
            item: Item identifier
            reason: Reason for skipping
        """
        self.skipped += 1
        self.update()
        if self.verbose:
            self.logger.info(f"⊘ {item} - SKIPPED: {reason}")

    def log_info(self, message: str):
        """Log info message.

        Args:
            message: Message to log
        """
        self.logger.info(message)

    def log_warning(self, message: str):
        """Log warning message.

        Args:
            message: Message to log
        """
        self.logger.warning(message)

    def log_debug(self, message: str):
        """Log debug message.

        Args:
            message: Message to log
        """
        if self.verbose:
            self.logger.debug(message)

    def set_description(self, desc: str):
        """Update progress bar description.

        Args:
            desc: New description
        """
        self.pbar.set_description(desc)

    def get_stats(self) -> dict:
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

    def print_summary(self):
        """Print final summary."""
        self.pbar.close()
        stats = self.get_stats()
        self.logger.info("\n" + "=" * 60)
        self.logger.info("SCRAPING SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total items:     {stats['total']}")
        self.logger.info(f"Completed:       {stats['completed']}")
        self.logger.info(f"Failed:          {stats['failed']}")
        self.logger.info(f"Skipped:         {stats['skipped']}")
        success_rate = (
            (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        )
        self.logger.info(f"Success rate:    {success_rate:.1f}%")
        self.logger.info("=" * 60)

    def close(self):
        """Close progress bar and handlers."""
        self.pbar.close()
        for handler in self.logger.handlers:
            handler.close()
