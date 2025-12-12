"""CSV validation utilities."""

from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from webscraper.exceptions import ValidationError
from webscraper.validation.base import BaseValidator


class CSVValidator(BaseValidator):
    """Validates downloaded CSV files.

    Features:
    - File size validation
    - Encoding detection (utf-8, iso-8859-1, windows-1252)
    - Delimiter detection (comma, semicolon)
    - Required column checking
    - Minimum row count validation
    - Custom validator support

    Example:
        >>> validator = CSVValidator(min_file_size=100, min_rows=1)
        >>> validator.validate_file(Path("data.csv"))
        True
    """

    def __init__(
        self,
        min_file_size: int = 100,
        required_columns: Optional[list[str]] = None,
        min_rows: int = 0,
        custom_validators: Optional[list[Callable[[pd.DataFrame], None]]] = None,
    ) -> None:
        """Initialize CSV validator.

        Args:
            min_file_size: Minimum file size in bytes
            required_columns: List of required column names
            min_rows: Minimum number of rows expected
            custom_validators: List of custom validation functions that
                              take a DataFrame and raise ValidationError on failure
        """
        self.min_file_size = min_file_size
        self.required_columns = required_columns or []
        self.min_rows = min_rows
        self.custom_validators = custom_validators or []

    def validate_file(self, file_path: Path) -> bool:
        """Validate a CSV file.

        Args:
            file_path: Path to CSV file

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        # Check file exists
        if not file_path.exists():
            raise ValidationError(f"File does not exist: {file_path}")

        # Check file size
        file_size = file_path.stat().st_size
        if file_size < self.min_file_size:
            raise ValidationError(
                f"File too small ({file_size} bytes, minimum {self.min_file_size})"
            )

        # Try to read as CSV with different encodings and delimiters
        encodings = ["utf-8", "iso-8859-1", "windows-1252", "latin1"]
        delimiters = [",", ";"]
        df: Optional[pd.DataFrame] = None
        last_error: Optional[Exception] = None

        for encoding in encodings:
            for delimiter in delimiters:
                try:
                    df = pd.read_csv(
                        file_path,
                        encoding=encoding,
                        sep=delimiter,
                        encoding_errors="ignore",
                    )
                    # Check if we actually parsed columns (not just one giant column)
                    if len(df.columns) > 1:
                        break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    last_error = e
                    continue

            if df is not None and len(df.columns) > 1:
                break

        if df is None or len(df.columns) <= 1:
            raise ValidationError(
                f"Failed to read CSV with any encoding/delimiter: {last_error}"
            )

        # Check for empty dataframe
        if df.empty and self.min_rows > 0:
            raise ValidationError("CSV file is empty")

        # Check row count
        if len(df) < self.min_rows:
            raise ValidationError(
                f"Insufficient rows ({len(df)}, minimum {self.min_rows})"
            )

        # Check required columns
        if self.required_columns:
            missing_cols = set(self.required_columns) - set(df.columns)
            if missing_cols:
                raise ValidationError(f"Missing required columns: {missing_cols}")

        # Run custom validators
        for validator in self.custom_validators:
            try:
                validator(df)
            except Exception as e:
                raise ValidationError(f"Custom validation failed: {e}")

        return True

    def quick_validate(self, file_path: Path) -> bool:
        """Quick validation (file exists and minimum size).

        Args:
            file_path: Path to CSV file

        Returns:
            True if valid, False otherwise
        """
        try:
            if not file_path.exists():
                return False
            file_size = file_path.stat().st_size
            return file_size >= self.min_file_size
        except Exception:
            return False


def validate_date_format(df: pd.DataFrame) -> None:
    """Custom validator: Check if dataframe has date-like columns.

    Args:
        df: DataFrame to validate

    Raises:
        ValidationError: If no date columns found
    """
    date_like_columns = [
        col
        for col in df.columns
        if any(
            keyword in col.lower()
            for keyword in ["date", "time", "datetime", "timestamp"]
        )
    ]
    if not date_like_columns:
        raise ValidationError("No date-like columns found in CSV")


def validate_numeric_data(df: pd.DataFrame) -> None:
    """Custom validator: Check if dataframe has numeric data columns.

    Args:
        df: DataFrame to validate

    Raises:
        ValidationError: If no numeric columns found
    """
    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
    if len(numeric_cols) == 0:
        raise ValidationError("No numeric columns found in CSV")


def create_jao_validator() -> CSVValidator:
    """Create a validator configured for JAO data.

    Returns:
        CSVValidator instance configured for JAO
    """
    return CSVValidator(
        min_file_size=50,  # JAO files might be small for some dates
        min_rows=0,  # Some dates may have no data
    )
