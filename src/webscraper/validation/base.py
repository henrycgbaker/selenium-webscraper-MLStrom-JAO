"""Base validator interface."""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseValidator(ABC):
    """Abstract base class for data validators.

    Subclasses should implement validate_file() to provide
    custom validation logic for different file types.
    """

    @abstractmethod
    def validate_file(self, file_path: Path) -> bool:
        """Validate a file.

        Args:
            file_path: Path to file to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        ...

    @abstractmethod
    def quick_validate(self, file_path: Path) -> bool:
        """Quick validation (file exists and meets minimum requirements).

        Args:
            file_path: Path to file to validate

        Returns:
            True if valid, False otherwise (no exceptions)
        """
        ...
