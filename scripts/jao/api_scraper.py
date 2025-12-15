#!/usr/bin/env python3
"""JAO MaxNetPos API Scraper.

This script downloads the complete JAO maxNetPos dataset using the direct API.
This is faster and more reliable than browser automation.

Usage:
    python -m scripts.jao.api_scraper --start-date 2022-06-08 --end-date 2024-12-31

Or run directly:
    python scripts/jao/api_scraper.py
"""

import csv
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

# Add project root to path for direct execution
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.jao.config import (
    DEFAULT_END_DATE,
    DEFAULT_REQUESTS_PER_MINUTE,
    DEFAULT_START_DATE,
    JAO_API_URL,
    JAO_BASE_URL,
)
from webscraper.core.clients.http import HttpClient
from webscraper.core.config import ScraperConfig
from webscraper.exceptions import HttpClientError
from webscraper.scrapers.base import BaseScraper
from webscraper.validation.csv import CSVValidator, create_jao_validator


class JAOAPIScraper(BaseScraper):
    """Scraper for JAO maxNetPos data using the direct API.

    This scraper uses the JAO JSON API to fetch data and converts it to CSV.
    Much faster than Selenium-based scraping.

    Example:
        >>> config = ScraperConfig(output_dir=Path("./data"))
        >>> with JAOAPIScraper(config) as scraper:
        ...     scraper.run(date(2024, 1, 1), date(2024, 1, 31))
    """

    def __init__(
        self,
        config: ScraperConfig,
        api_url: str = JAO_API_URL,
    ) -> None:
        """Initialize JAO API scraper.

        Args:
            config: Scraper configuration
            api_url: JAO API endpoint URL
        """
        super().__init__(config)
        self.api_url = api_url
        self._http_client: Optional[HttpClient] = None

    @property
    def http_client(self) -> HttpClient:
        """Get HTTP client (lazy initialization)."""
        if self._http_client is None:
            self._http_client = HttpClient(
                base_url=JAO_BASE_URL,
                timeout=self.config.request_timeout,
                max_retries=self.config.max_retries,
                retry_delay=self.config.retry_delay,
            )
            self._http_client.set_headers(
                {
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (compatible; JAOScraper/1.0)",
                }
            )
        return self._http_client

    def get_validator(self) -> CSVValidator:
        """Get validator for JAO CSV files."""
        return create_jao_validator()

    def download_for_date(self, target_date: date) -> Optional[Path]:
        """Download data for a specific date using the API.

        Args:
            target_date: Date to download data for

        Returns:
            Path to downloaded file, or None if failed
        """
        # Fetch data from API
        data = self._fetch_data(target_date)

        if not data:
            raise RuntimeError(f"No data returned for {target_date}")

        # Define output path
        output_filename = f"maxNetPos_{target_date.strftime('%Y%m%d')}.csv"
        output_path = self.config.output_dir / output_filename

        # Convert JSON to CSV
        self._save_as_csv(data, output_path)

        return output_path

    def _fetch_data(self, target_date: date) -> list[dict[str, Any]]:
        """Fetch data from JAO API for a specific date.

        Args:
            target_date: Date to fetch data for

        Returns:
            List of data records

        Raises:
            HttpClientError: If request fails after retries
        """
        self.rate_limiter.wait_if_needed()

        from_utc = f"{target_date.isoformat()}T00:00:00.000Z"
        to_utc = f"{(target_date + timedelta(days=1)).isoformat()}T00:00:00.000Z"

        params = {"FromUtc": from_utc, "ToUtc": to_utc}

        try:
            response = self.http_client.get("api/data/maxNetPos", params=params)
            json_data = response.json()
            return json_data.get("data", [])
        except HttpClientError as e:
            if "429" in str(e) or "rate limit" in str(e).lower():
                self.rate_limiter.on_429_response(self.config.retry_delay)
            raise

    def _save_as_csv(self, data: list[dict[str, Any]], output_path: Path) -> None:
        """Save data as CSV file.

        Args:
            data: List of data records
            output_path: Path to save CSV file
        """
        if not data:
            return

        fieldnames = list(data[0].keys())

        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(data)

    def cleanup(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            self._http_client.close()
            self._http_client = None


def run_jao_api_scraper(
    start_date: date = DEFAULT_START_DATE,
    end_date: date = DEFAULT_END_DATE,
    output_dir: Path = Path("./data"),
    requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
    verbose: bool = False,
) -> None:
    """Run the JAO API scraper.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        output_dir: Directory to save downloaded files
        requests_per_minute: Rate limit
        verbose: Enable verbose logging
    """
    print("=" * 60)
    print("JAO MaxNetPos API Scraper")
    print("=" * 60)
    print(f"Date range: {start_date} to {end_date}")
    print(f"Output directory: {output_dir}")
    print("")

    config = ScraperConfig(
        output_dir=output_dir,
        requests_per_minute=requests_per_minute,
        verbose=verbose,
    )

    with JAOAPIScraper(config) as scraper:
        scraper.run(start_date, end_date)

    print("\nDone!")


if __name__ == "__main__":
    import typer

    def main(
        start_date: str = typer.Option(
            DEFAULT_START_DATE.isoformat(),
            "--start-date",
            "-s",
            help="Start date (YYYY-MM-DD)",
        ),
        end_date: str = typer.Option(
            DEFAULT_END_DATE.isoformat(),
            "--end-date",
            "-e",
            help="End date (YYYY-MM-DD)",
        ),
        output_dir: Path = typer.Option(
            Path("./data"),
            "--output-dir",
            "-o",
            help="Output directory",
        ),
        rate_limit: int = typer.Option(
            DEFAULT_REQUESTS_PER_MINUTE,
            "--rate-limit",
            help="Requests per minute",
        ),
        verbose: bool = typer.Option(
            False,
            "--verbose",
            "-v",
            help="Verbose output",
        ),
    ) -> None:
        """Download JAO maxNetPos data using the API."""
        from datetime import datetime

        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        run_jao_api_scraper(
            start_date=start,
            end_date=end,
            output_dir=output_dir,
            requests_per_minute=rate_limit,
            verbose=verbose,
        )

    typer.run(main)
