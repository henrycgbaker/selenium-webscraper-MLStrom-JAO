"""Tests for state management module."""

from pathlib import Path

import pytest

from webscraper.core.state import DownloadStatus, StateManager


class TestStateManager:
    """Tests for StateManager."""

    def test_init_creates_state(self, tmp_path: Path) -> None:
        """Test that initialization creates state structure."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)

        assert "downloads" in manager.state
        assert "metadata" in manager.state
        assert "created_at" in manager.state

    def test_get_status_default(self, state_manager: StateManager) -> None:
        """Test that unknown dates return PENDING status."""
        status = state_manager.get_status("2024-01-01")
        assert status == DownloadStatus.PENDING

    def test_set_and_get_status(self, state_manager: StateManager) -> None:
        """Test setting and retrieving status."""
        state_manager.set_status("2024-01-01", DownloadStatus.COMPLETED)
        status = state_manager.get_status("2024-01-01")
        assert status == DownloadStatus.COMPLETED

    def test_set_status_with_file_path(self, state_manager: StateManager) -> None:
        """Test setting status with file path."""
        state_manager.set_status(
            "2024-01-01",
            DownloadStatus.COMPLETED,
            file_path="/path/to/file.csv",
        )

        assert state_manager.state["downloads"]["2024-01-01"]["file_path"] == "/path/to/file.csv"

    def test_set_status_with_error(self, state_manager: StateManager) -> None:
        """Test setting status with error message."""
        state_manager.set_status(
            "2024-01-01",
            DownloadStatus.FAILED,
            error="Connection timeout",
        )

        assert state_manager.state["downloads"]["2024-01-01"]["error"] == "Connection timeout"

    def test_get_completed_dates(self, state_manager: StateManager) -> None:
        """Test getting completed dates."""
        state_manager.set_status("2024-01-01", DownloadStatus.COMPLETED)
        state_manager.set_status("2024-01-02", DownloadStatus.FAILED)
        state_manager.set_status("2024-01-03", DownloadStatus.COMPLETED)

        completed = state_manager.get_completed_dates()

        assert "2024-01-01" in completed
        assert "2024-01-02" not in completed
        assert "2024-01-03" in completed

    def test_get_failed_dates(self, state_manager: StateManager) -> None:
        """Test getting failed dates."""
        state_manager.set_status("2024-01-01", DownloadStatus.COMPLETED)
        state_manager.set_status("2024-01-02", DownloadStatus.FAILED)

        failed = state_manager.get_failed_dates()

        assert "2024-01-01" not in failed
        assert "2024-01-02" in failed

    def test_get_pending_dates(self, state_manager: StateManager) -> None:
        """Test getting pending dates from a list."""
        all_dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        state_manager.set_status("2024-01-01", DownloadStatus.COMPLETED)

        pending = state_manager.get_pending_dates(all_dates)

        assert "2024-01-01" not in pending
        assert "2024-01-02" in pending
        assert "2024-01-03" in pending

    def test_attempts_tracking(self, state_manager: StateManager) -> None:
        """Test that attempts are tracked correctly."""
        assert state_manager.get_attempts("2024-01-01") == 0

        state_manager.set_status("2024-01-01", DownloadStatus.IN_PROGRESS)
        assert state_manager.get_attempts("2024-01-01") == 1

        state_manager.set_status("2024-01-01", DownloadStatus.FAILED)
        assert state_manager.get_attempts("2024-01-01") == 2

    def test_metadata(self, state_manager: StateManager) -> None:
        """Test metadata storage and retrieval."""
        state_manager.set_metadata("api_url", "https://example.com")
        value = state_manager.get_metadata("api_url")

        assert value == "https://example.com"

    def test_metadata_default(self, state_manager: StateManager) -> None:
        """Test metadata default value."""
        value = state_manager.get_metadata("nonexistent", default="default")
        assert value == "default"

    def test_get_summary(self, state_manager: StateManager) -> None:
        """Test summary statistics."""
        state_manager.set_status("2024-01-01", DownloadStatus.COMPLETED)
        state_manager.set_status("2024-01-02", DownloadStatus.COMPLETED)
        state_manager.set_status("2024-01-03", DownloadStatus.FAILED)

        summary = state_manager.get_summary()

        assert summary["total"] == 3
        assert summary["completed"] == 2
        assert summary["failed"] == 1
        assert summary["success_rate"] == pytest.approx(66.67, rel=0.1)

    def test_reset(self, state_manager: StateManager) -> None:
        """Test state reset."""
        state_manager.set_status("2024-01-01", DownloadStatus.COMPLETED)
        state_manager.reset()

        assert len(state_manager.state["downloads"]) == 0

    def test_persistence(self, tmp_path: Path) -> None:
        """Test that state persists to file."""
        state_file = tmp_path / "state.json"

        # Create and populate state
        manager1 = StateManager(state_file)
        manager1.set_status("2024-01-01", DownloadStatus.COMPLETED)

        # Create new manager from same file
        manager2 = StateManager(state_file)
        status = manager2.get_status("2024-01-01")

        assert status == DownloadStatus.COMPLETED
