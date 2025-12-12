"""Pytest configuration and fixtures."""

from pathlib import Path
from typing import Generator

import pytest

from webscraper.core.config import ScraperConfig
from webscraper.core.state import StateManager


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_config(tmp_output_dir: Path) -> ScraperConfig:
    """Create a sample scraper configuration."""
    return ScraperConfig(
        output_dir=tmp_output_dir,
        requests_per_minute=60,
        verbose=False,
    )


@pytest.fixture
def state_manager(tmp_path: Path) -> Generator[StateManager, None, None]:
    """Create a temporary state manager."""
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)
    yield manager


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Create a sample CSV file for testing."""
    csv_content = """date,value,name
2024-01-01,100,test1
2024-01-02,200,test2
2024-01-03,300,test3
"""
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(csv_content)
    return csv_path


@pytest.fixture
def empty_csv(tmp_path: Path) -> Path:
    """Create an empty CSV file for testing."""
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("date,value\n")
    return csv_path


@pytest.fixture
def small_file(tmp_path: Path) -> Path:
    """Create a file smaller than minimum size."""
    small_path = tmp_path / "small.csv"
    small_path.write_text("a")
    return small_path
