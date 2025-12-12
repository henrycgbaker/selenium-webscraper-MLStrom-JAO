#!/usr/bin/env python3
"""Example: Basic Selenium-based scraper.

This example shows how to create a scraper that uses browser automation
to download files from websites that require JavaScript interaction.

Run with:
    python scripts/examples/basic_selenium_scraper.py
"""

import sys
import time
from datetime import date
from pathlib import Path
from typing import Optional

# Add project root to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webscraper import BaseScraper, BrowserClient, CSVValidator, ScraperConfig
from webscraper.exceptions import BrowserClientError


class ExampleSeleniumScraper(BaseScraper):
    """Example scraper demonstrating Selenium-based automation.

    This scraper automates a web browser to:
    1. Navigate to a page
    2. Fill in a date field
    3. Click a download button
    4. Wait for the file to download

    Replace the URL and selectors with your target website.
    """

    # Replace with your target URL
    PAGE_URL = "https://example.com/data-export"

    # Replace with your page's CSS selectors
    SELECTORS = {
        "date_input": "#date-picker",
        "download_button": "#download-btn",
    }

    def __init__(self, config: ScraperConfig) -> None:
        super().__init__(config)
        self._browser: Optional[BrowserClient] = None

    @property
    def browser(self) -> BrowserClient:
        """Lazy-initialize browser client."""
        if self._browser is None:
            self._browser = BrowserClient(
                headless=self.config.headless,
                browser=self.config.browser,
                download_dir=self.config.output_dir,
                page_load_timeout=self.config.selenium_page_load_timeout,
                element_wait_timeout=self.config.selenium_element_wait_timeout,
            )
            self._browser.start()
        return self._browser

    def get_validator(self) -> CSVValidator:
        """Return validator for downloaded files."""
        return CSVValidator(
            min_file_size=100,
            min_rows=1,
        )

    def download_for_date(self, target_date: date) -> Optional[Path]:
        """Download data for a specific date using browser automation.

        Args:
            target_date: Date to download data for

        Returns:
            Path to downloaded file
        """
        # Navigate to page
        self.browser.navigate(self.PAGE_URL)

        # Wait for page to load
        time.sleep(2)

        # Capture existing files before download
        existing_files = self.browser.get_existing_files()

        # Fill in date field
        # Adjust based on your page's date picker implementation
        date_str = target_date.strftime("%Y-%m-%d")
        self.browser.send_keys(self.SELECTORS["date_input"], date_str)
        time.sleep(0.5)

        # Click download button
        self.browser.click(self.SELECTORS["download_button"])

        # Wait for download to complete
        downloaded_file = self.browser.wait_for_download(
            timeout=self.config.download_timeout,
            existing_files=existing_files,
        )

        if downloaded_file is None:
            raise BrowserClientError("Download timeout - no file received")

        # Rename to standardized filename
        output_path = self.config.output_dir / f"data_{target_date:%Y%m%d}.csv"
        if downloaded_file != output_path:
            if output_path.exists():
                output_path.unlink()
            downloaded_file.rename(output_path)

        return output_path

    def cleanup(self) -> None:
        """Close browser."""
        if self._browser:
            self._browser.quit()


def main() -> None:
    """Run the example scraper."""
    print("Example Selenium Scraper")
    print("=" * 40)
    print()
    print("This is a template showing how to create a Selenium-based scraper.")
    print("To use it:")
    print("  1. Replace PAGE_URL with your target website")
    print("  2. Update SELECTORS with your page's CSS selectors")
    print("  3. Adjust the interaction logic in download_for_date()")
    print()
    print("Example usage:")
    print("  config = ScraperConfig(output_dir=Path('./data'), headless=True)")
    print("  with ExampleSeleniumScraper(config) as scraper:")
    print("      scraper.run(date(2024, 1, 1), date(2024, 1, 31))")
    print()
    print("Tips:")
    print("  - Use browser DevTools to find CSS selectors")
    print("  - Test with --headed first to see browser interactions")
    print("  - Add time.sleep() calls for JavaScript-heavy pages")


if __name__ == "__main__":
    main()
