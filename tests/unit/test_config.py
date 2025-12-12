"""Tests for configuration module."""

from pathlib import Path

import pytest

from webscraper.core.config import ScraperConfig


class TestScraperConfig:
    """Tests for ScraperConfig."""

    def test_basic_config(self, tmp_path: Path) -> None:
        """Test basic configuration creation."""
        config = ScraperConfig(output_dir=tmp_path / "output")

        assert config.output_dir.exists()
        assert config.state_file is not None
        assert config.requests_per_minute == 60
        assert config.headless is True

    def test_string_path_conversion(self, tmp_path: Path) -> None:
        """Test that string paths are converted to Path objects."""
        config = ScraperConfig(output_dir=str(tmp_path / "output"))

        assert isinstance(config.output_dir, Path)

    def test_default_state_file(self, tmp_path: Path) -> None:
        """Test that state file defaults to output_dir/scraper_state.json."""
        config = ScraperConfig(output_dir=tmp_path / "output")

        assert config.state_file == config.output_dir / "scraper_state.json"

    def test_custom_state_file(self, tmp_path: Path) -> None:
        """Test custom state file path."""
        state_file = tmp_path / "custom_state.json"
        config = ScraperConfig(
            output_dir=tmp_path / "output",
            state_file=state_file,
        )

        assert config.state_file == state_file

    def test_invalid_browser(self, tmp_path: Path) -> None:
        """Test that invalid browser raises validation error."""
        with pytest.raises(Exception):  # Pydantic validation error
            ScraperConfig(
                output_dir=tmp_path / "output",
                browser="safari",  # Invalid
            )

    def test_rate_limit_bounds(self, tmp_path: Path) -> None:
        """Test rate limit validation."""
        # Valid
        config = ScraperConfig(
            output_dir=tmp_path / "output",
            requests_per_minute=100,
        )
        assert config.requests_per_minute == 100

        # Invalid - too low
        with pytest.raises(Exception):
            ScraperConfig(
                output_dir=tmp_path / "output",
                requests_per_minute=0,
            )

    def test_to_dict(self, tmp_path: Path) -> None:
        """Test config serialization to dict."""
        config = ScraperConfig(output_dir=tmp_path / "output")
        config_dict = config.to_dict()

        assert "output_dir" in config_dict
        assert "requests_per_minute" in config_dict
        assert config_dict["requests_per_minute"] == 60
