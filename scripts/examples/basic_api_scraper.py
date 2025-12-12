#!/usr/bin/env python3
"""Example: Basic API-based scraper.

This example shows how to create a simple scraper that downloads data
from a JSON API and saves it as CSV files.

Run with:
    python scripts/examples/basic_api_scraper.py
"""

import csv
import sys
from datetime import date
from pathlib import Path
from typing import Any, Optional

# Add project root to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests

from webscraper import BaseScraper, CSVValidator, ScraperConfig


class ExampleAPIScraper(BaseScraper):
    """Example scraper demonstrating API-based data collection.

    This scraper fetches JSON data from an API endpoint and converts
    it to CSV format. Replace the API_URL and data handling logic
    with your target API.
    """

    # Replace with your target API URL
    API_URL = "https://api.example.com/data"

    def __init__(self, config: ScraperConfig) -> None:
        super().__init__(config)
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        """Lazy-initialize HTTP session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(
                {
                    "Accept": "application/json",
                    "User-Agent": "ExampleScraper/1.0",
                }
            )
        return self._session

    def get_validator(self) -> CSVValidator:
        """Return validator for downloaded files."""
        return CSVValidator(
            min_file_size=50,
            min_rows=0,
        )

    def download_for_date(self, target_date: date) -> Optional[Path]:
        """Download data for a specific date.

        Args:
            target_date: Date to download data for

        Returns:
            Path to downloaded CSV file
        """
        # Fetch data from API
        # Replace this with your actual API call
        params = {
            "date": target_date.isoformat(),
            "format": "json",
        }

        response = self.session.get(
            self.API_URL,
            params=params,
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()

        # Parse JSON response
        # Adjust based on your API's response structure
        data = response.json()
        records = data.get("data", data.get("results", []))

        if not records:
            raise RuntimeError(f"No data returned for {target_date}")

        # Save as CSV
        output_path = self.config.output_dir / f"data_{target_date:%Y%m%d}.csv"
        self._save_csv(records, output_path)

        return output_path

    def _save_csv(self, records: list[dict[str, Any]], output_path: Path) -> None:
        """Save records as CSV file."""
        if not records:
            return

        fieldnames = list(records[0].keys())

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

    def cleanup(self) -> None:
        """Close HTTP session."""
        if self._session:
            self._session.close()


def main() -> None:
    """Run the example scraper."""
    print("Example API Scraper")
    print("=" * 40)
    print()
    print("This is a template showing how to create an API-based scraper.")
    print("To use it:")
    print("  1. Replace API_URL with your target API")
    print("  2. Adjust the params in download_for_date()")
    print("  3. Update the JSON parsing logic for your API's response format")
    print()
    print("Example usage:")
    print("  config = ScraperConfig(output_dir=Path('./data'))")
    print("  with ExampleAPIScraper(config) as scraper:")
    print("      scraper.run(date(2024, 1, 1), date(2024, 1, 31))")


if __name__ == "__main__":
    main()
