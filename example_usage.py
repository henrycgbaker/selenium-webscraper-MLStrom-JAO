"""Example usage of the web scraper framework.

This script demonstrates how to use the scraper programmatically
without using the CLI interface.
"""

from datetime import date
from pathlib import Path

from config import ScraperConfig
from scrapers.jao_scraper import JAOScraper


def example_basic_usage():
    """Basic example: Download JAO data for a date range."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)

    # Configure the scraper
    config = ScraperConfig(
        output_dir=Path("./example_output"),
        requests_per_minute=60,
        validate_downloads=True,
        verbose=True,
        headless=True,
    )

    # Create scraper instance
    scraper = JAOScraper(config)

    # Download data for a specific date range
    start = date(2024, 1, 1)
    end = date(2024, 1, 5)

    print(f"Downloading data from {start} to {end}")
    scraper.run(start_date=start, end_date=end, resume=True)

    # Cleanup
    scraper.cleanup()

    print("\nDone! Files saved to:", config.output_dir)


def example_custom_config():
    """Example with custom configuration."""
    print("\n" + "=" * 60)
    print("Example 2: Custom Configuration")
    print("=" * 60)

    # Custom configuration with all options
    config = ScraperConfig(
        output_dir=Path("./custom_output"),
        state_file=Path("./custom_state.json"),
        requests_per_minute=30,  # Lower rate limit
        retry_delay=120,  # Wait 2 minutes on 429
        max_retries=5,  # Try up to 5 times
        request_timeout=60,  # 60 second timeout
        validate_downloads=True,
        min_file_size=50,  # Minimum 50 bytes
        verbose=True,
        log_file=Path("./scraper.log"),
        headless=False,  # Show browser window
        browser="chrome",
    )

    with JAOScraper(config) as scraper:
        scraper.run(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 3),
            resume=True,
        )

    print("\nConfiguration used:")
    print(config.to_dict())


def example_check_status():
    """Example: Check status of a previous run."""
    print("\n" + "=" * 60)
    print("Example 3: Check Status")
    print("=" * 60)

    from utils.state import StateManager

    state_file = Path("./example_output/scraper_state.json")

    if not state_file.exists():
        print(f"State file not found: {state_file}")
        print("Run example_basic_usage() first.")
        return

    state = StateManager(state_file)
    summary = state.get_summary()

    print(f"State file: {state_file}")
    print(f"\nSummary:")
    print(f"  Total:      {summary['total']}")
    print(f"  Completed:  {summary['completed']}")
    print(f"  Failed:     {summary['failed']}")
    print(f"  Pending:    {summary['pending']}")
    print(f"  Success:    {summary['success_rate']:.1f}%")

    # Show failed dates
    failed = state.get_failed_dates()
    if failed:
        print(f"\nFailed dates ({len(failed)}):")
        for date_str in sorted(failed):
            info = state.state["downloads"][date_str]
            error = info.get("error", "Unknown")
            print(f"  {date_str}: {error}")


def example_custom_scraper():
    """Example: Create a custom scraper for another website."""
    print("\n" + "=" * 60)
    print("Example 4: Custom Scraper Template")
    print("=" * 60)

    from scrapers.base import BaseScraper
    from utils.validation import CSVValidator

    class MyCustomScraper(BaseScraper):
        """Custom scraper for another website."""

        def download_for_date(self, target_date: date) -> Path:
            """Download data for a specific date."""
            # TODO: Implement your download logic here

            # Example: API-based download
            # from core.api_client import APIClient
            # client = APIClient("https://api.example.com")
            # client.set_headers({"Authorization": "Bearer TOKEN"})
            # params = {"date": target_date.strftime("%Y-%m-%d")}
            # output_path = self.config.output_dir / f"data_{target_date:%Y%m%d}.csv"
            # return client.download_file("/export", output_path, params=params)

            # Example: Selenium-based download
            # from core.selenium_client import SeleniumClient
            # client = SeleniumClient(headless=True, download_dir=self.config.output_dir)
            # client.start()
            # client.navigate("https://example.com/data")
            # client.send_keys("#date", target_date.strftime("%Y-%m-%d"))
            # client.click("#download")
            # file_path = client.wait_for_download()
            # client.quit()
            # return file_path

            print(f"Would download data for {target_date}")
            return None

        def get_validator(self) -> CSVValidator:
            """Get validator for downloaded files."""
            return CSVValidator(
                min_file_size=100,
                required_columns=["date", "value"],
                min_rows=1,
            )

    print("Custom scraper template created.")
    print("See the class definition above for implementation details.")

    # Usage:
    # config = ScraperConfig(output_dir=Path("./custom_data"))
    # scraper = MyCustomScraper(config)
    # scraper.run(start_date=date(2024, 1, 1), end_date=date(2024, 1, 31))


def main():
    """Run all examples."""
    print("\nWeb Scraper Framework - Usage Examples\n")

    # Example 1: Basic usage
    # Uncomment to run:
    # example_basic_usage()

    # Example 2: Custom configuration
    # Uncomment to run:
    # example_custom_config()

    # Example 3: Check status
    # Uncomment to run:
    # example_check_status()

    # Example 4: Custom scraper template
    example_custom_scraper()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
    print("\nTo run an example, uncomment it in the main() function.")


if __name__ == "__main__":
    main()
