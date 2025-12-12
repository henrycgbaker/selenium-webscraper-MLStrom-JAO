"""Tests for validation module."""

from pathlib import Path

import pytest

from webscraper.exceptions import ValidationError
from webscraper.validation.csv import CSVValidator, create_jao_validator


class TestCSVValidator:
    """Tests for CSVValidator."""

    def test_validate_valid_file(self, sample_csv: Path) -> None:
        """Test validation of a valid CSV file."""
        validator = CSVValidator(min_file_size=10, min_rows=1)
        result = validator.validate_file(sample_csv)
        assert result is True

    def test_validate_file_not_exists(self, tmp_path: Path) -> None:
        """Test validation of non-existent file."""
        validator = CSVValidator()
        with pytest.raises(ValidationError, match="does not exist"):
            validator.validate_file(tmp_path / "nonexistent.csv")

    def test_validate_file_too_small(self, small_file: Path) -> None:
        """Test validation of file smaller than minimum size."""
        validator = CSVValidator(min_file_size=100)
        with pytest.raises(ValidationError, match="too small"):
            validator.validate_file(small_file)

    def test_validate_empty_csv(self, empty_csv: Path) -> None:
        """Test validation of empty CSV with min_rows > 0."""
        validator = CSVValidator(min_file_size=1, min_rows=1)
        with pytest.raises(ValidationError, match="(empty|Insufficient rows)"):
            validator.validate_file(empty_csv)

    def test_validate_required_columns(self, sample_csv: Path) -> None:
        """Test validation of required columns."""
        # Valid - columns exist
        validator = CSVValidator(
            min_file_size=1,
            required_columns=["date", "value"],
        )
        result = validator.validate_file(sample_csv)
        assert result is True

        # Invalid - missing column
        validator = CSVValidator(
            min_file_size=1,
            required_columns=["date", "nonexistent"],
        )
        with pytest.raises(ValidationError, match="Missing required columns"):
            validator.validate_file(sample_csv)

    def test_quick_validate(self, sample_csv: Path, small_file: Path) -> None:
        """Test quick validation."""
        validator = CSVValidator(min_file_size=10)

        # Valid file
        assert validator.quick_validate(sample_csv) is True

        # Too small
        assert validator.quick_validate(small_file) is False

    def test_quick_validate_nonexistent(self, tmp_path: Path) -> None:
        """Test quick validation of non-existent file."""
        validator = CSVValidator()
        assert validator.quick_validate(tmp_path / "nonexistent.csv") is False

    def test_custom_validator(self, sample_csv: Path) -> None:
        """Test custom validator function."""

        def check_has_date_column(df) -> None:  # type: ignore[no-untyped-def]
            if "date" not in df.columns:
                raise ValueError("No date column")

        validator = CSVValidator(
            min_file_size=1,
            custom_validators=[check_has_date_column],
        )
        result = validator.validate_file(sample_csv)
        assert result is True

    def test_create_jao_validator(self) -> None:
        """Test JAO validator factory."""
        validator = create_jao_validator()

        assert validator.min_file_size == 50
        assert validator.min_rows == 0


class TestSemicolonDelimitedCSV:
    """Tests for semicolon-delimited CSV files."""

    def test_validate_semicolon_csv(self, tmp_path: Path) -> None:
        """Test validation of semicolon-delimited CSV."""
        csv_content = """date;value;name
2024-01-01;100;test1
2024-01-02;200;test2
"""
        csv_path = tmp_path / "semicolon.csv"
        csv_path.write_text(csv_content)

        validator = CSVValidator(min_file_size=1)
        result = validator.validate_file(csv_path)
        assert result is True
