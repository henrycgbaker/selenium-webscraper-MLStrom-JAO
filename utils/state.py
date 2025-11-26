"""State management for resume capability."""
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime, date
from enum import Enum
import threading


class DownloadStatus(str, Enum):
    """Status of a download."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StateManager:
    """Manages scraper state for resume capability."""

    def __init__(self, state_file: Path):
        """Initialize state manager.

        Args:
            state_file: Path to JSON file storing state
        """
        self.state_file = state_file
        self.state: Dict = self._load_state()
        self._lock = threading.Lock()

    def _load_state(self) -> Dict:
        """Load state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._init_state()
        return self._init_state()

    def _init_state(self) -> Dict:
        """Initialize empty state structure."""
        return {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "downloads": {},  # date_str -> {status, file_path, error, attempts}
            "metadata": {},  # additional metadata
        }

    def _save_state(self):
        """Save state to file."""
        with self._lock:
            self.state["last_updated"] = datetime.now().isoformat()
            with open(self.state_file, "w") as f:
                json.dump(self.state, indent=2, fp=f)

    def get_status(self, date_key: str) -> DownloadStatus:
        """Get status for a specific date.

        Args:
            date_key: Date string (YYYY-MM-DD)

        Returns:
            DownloadStatus enum value
        """
        with self._lock:
            if date_key in self.state["downloads"]:
                return DownloadStatus(self.state["downloads"][date_key]["status"])
            return DownloadStatus.PENDING

    def set_status(
        self,
        date_key: str,
        status: DownloadStatus,
        file_path: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Set status for a specific date.

        Args:
            date_key: Date string (YYYY-MM-DD)
            status: New status
            file_path: Path to downloaded file (if completed)
            error: Error message (if failed)
        """
        with self._lock:
            if date_key not in self.state["downloads"]:
                self.state["downloads"][date_key] = {
                    "status": status.value,
                    "file_path": file_path,
                    "error": error,
                    "attempts": 0,
                    "created_at": datetime.now().isoformat(),
                }
            else:
                self.state["downloads"][date_key]["status"] = status.value
                if file_path:
                    self.state["downloads"][date_key]["file_path"] = file_path
                if error:
                    self.state["downloads"][date_key]["error"] = error
                self.state["downloads"][date_key]["updated_at"] = datetime.now().isoformat()

            if status in [DownloadStatus.IN_PROGRESS, DownloadStatus.FAILED]:
                self.state["downloads"][date_key]["attempts"] += 1

        self._save_state()

    def get_completed_dates(self) -> Set[str]:
        """Get set of completed dates."""
        with self._lock:
            return {
                date_key
                for date_key, info in self.state["downloads"].items()
                if info["status"] == DownloadStatus.COMPLETED.value
            }

    def get_failed_dates(self) -> Set[str]:
        """Get set of failed dates."""
        with self._lock:
            return {
                date_key
                for date_key, info in self.state["downloads"].items()
                if info["status"] == DownloadStatus.FAILED.value
            }

    def get_pending_dates(self, all_dates: List[str]) -> List[str]:
        """Get list of pending dates from a list of all dates.

        Args:
            all_dates: List of all date strings to check

        Returns:
            List of dates that are not completed
        """
        completed = self.get_completed_dates()
        return [d for d in all_dates if d not in completed]

    def get_attempts(self, date_key: str) -> int:
        """Get number of attempts for a specific date."""
        with self._lock:
            if date_key in self.state["downloads"]:
                return self.state["downloads"][date_key].get("attempts", 0)
            return 0

    def set_metadata(self, key: str, value):
        """Set metadata value."""
        with self._lock:
            self.state["metadata"][key] = value
        self._save_state()

    def get_metadata(self, key: str, default=None):
        """Get metadata value."""
        with self._lock:
            return self.state["metadata"].get(key, default)

    def get_summary(self) -> Dict:
        """Get summary statistics."""
        with self._lock:
            total = len(self.state["downloads"])
            completed = sum(
                1
                for info in self.state["downloads"].values()
                if info["status"] == DownloadStatus.COMPLETED.value
            )
            failed = sum(
                1
                for info in self.state["downloads"].values()
                if info["status"] == DownloadStatus.FAILED.value
            )
            in_progress = sum(
                1
                for info in self.state["downloads"].values()
                if info["status"] == DownloadStatus.IN_PROGRESS.value
            )

            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "in_progress": in_progress,
                "pending": total - completed - failed - in_progress,
                "success_rate": (completed / total * 100) if total > 0 else 0,
            }

    def reset(self):
        """Reset state to empty."""
        self.state = self._init_state()
        self._save_state()
