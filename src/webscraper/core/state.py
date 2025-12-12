"""State management for resume capability."""

import json
import threading
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class DownloadStatus(str, Enum):
    """Status of a download operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StateManager:
    """Manages scraper state for resume capability.

    Persists download status to a JSON file, allowing scrapers to resume
    from where they left off after interruption.

    Example:
        >>> state = StateManager(Path("./state.json"))
        >>> state.set_status("2024-01-01", DownloadStatus.COMPLETED, file_path="data.csv")
        >>> state.get_status("2024-01-01")
        <DownloadStatus.COMPLETED: 'completed'>
    """

    def __init__(self, state_file: Path) -> None:
        """Initialize state manager.

        Args:
            state_file: Path to JSON file storing state
        """
        self.state_file = state_file
        self._state: dict[str, Any] = self._load_state()
        self._lock = threading.Lock()

    def _load_state(self) -> dict[str, Any]:
        """Load state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return self._init_state()
        return self._init_state()

    def _init_state(self) -> dict[str, Any]:
        """Initialize empty state structure."""
        return {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "downloads": {},
            "metadata": {},
        }

    def _save_state(self) -> None:
        """Save state to file."""
        with self._lock:
            self._state["last_updated"] = datetime.now().isoformat()
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self._state, f, indent=2)

    def get_status(self, date_key: str) -> DownloadStatus:
        """Get status for a specific date.

        Args:
            date_key: Date string (YYYY-MM-DD)

        Returns:
            DownloadStatus enum value
        """
        with self._lock:
            if date_key in self._state["downloads"]:
                return DownloadStatus(self._state["downloads"][date_key]["status"])
            return DownloadStatus.PENDING

    def set_status(
        self,
        date_key: str,
        status: DownloadStatus,
        file_path: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Set status for a specific date.

        Args:
            date_key: Date string (YYYY-MM-DD)
            status: New status
            file_path: Path to downloaded file (if completed)
            error: Error message (if failed)
        """
        with self._lock:
            if date_key not in self._state["downloads"]:
                self._state["downloads"][date_key] = {
                    "status": status.value,
                    "file_path": file_path,
                    "error": error,
                    "attempts": 0,
                    "created_at": datetime.now().isoformat(),
                }
            else:
                self._state["downloads"][date_key]["status"] = status.value
                if file_path:
                    self._state["downloads"][date_key]["file_path"] = file_path
                if error:
                    self._state["downloads"][date_key]["error"] = error
                self._state["downloads"][date_key][
                    "updated_at"
                ] = datetime.now().isoformat()

            if status in [DownloadStatus.IN_PROGRESS, DownloadStatus.FAILED]:
                self._state["downloads"][date_key]["attempts"] += 1

        self._save_state()

    def get_completed_dates(self) -> set[str]:
        """Get set of completed dates."""
        with self._lock:
            return {
                date_key
                for date_key, info in self._state["downloads"].items()
                if info["status"] == DownloadStatus.COMPLETED.value
            }

    def get_failed_dates(self) -> set[str]:
        """Get set of failed dates."""
        with self._lock:
            return {
                date_key
                for date_key, info in self._state["downloads"].items()
                if info["status"] == DownloadStatus.FAILED.value
            }

    def get_pending_dates(self, all_dates: list[str]) -> list[str]:
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
            if date_key in self._state["downloads"]:
                return int(self._state["downloads"][date_key].get("attempts", 0))
            return 0

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value."""
        with self._lock:
            self._state["metadata"][key] = value
        self._save_state()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        with self._lock:
            return self._state["metadata"].get(key, default)

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics."""
        with self._lock:
            total = len(self._state["downloads"])
            completed = sum(
                1
                for info in self._state["downloads"].values()
                if info["status"] == DownloadStatus.COMPLETED.value
            )
            failed = sum(
                1
                for info in self._state["downloads"].values()
                if info["status"] == DownloadStatus.FAILED.value
            )
            in_progress = sum(
                1
                for info in self._state["downloads"].values()
                if info["status"] == DownloadStatus.IN_PROGRESS.value
            )

            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "in_progress": in_progress,
                "pending": total - completed - failed - in_progress,
                "success_rate": (completed / total * 100) if total > 0 else 0.0,
            }

    def reset(self) -> None:
        """Reset state to empty."""
        self._state = self._init_state()
        self._save_state()

    @property
    def state(self) -> dict[str, Any]:
        """Access raw state dict (for backwards compatibility)."""
        return self._state
