#!/usr/bin/env python3
"""JAO MaxNetPos Selenium Scraper.

This script downloads JAO maxNetPos data using browser automation.
Use this if the API approach doesn't work or for debugging.

Usage:
    python -m scripts.jao.scraper --start-date 2024-01-01 --end-date 2024-01-31

Or run directly:
    python scripts/jao/scraper.py
"""

import sys
import time
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

# Add project root to path for direct execution
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.jao.config import (
    DEFAULT_END_DATE,
    DEFAULT_REQUESTS_PER_MINUTE,
    DEFAULT_START_DATE,
    JAO_PAGE_URL,
    JAO_SELECTORS,
)
from webscraper.core.clients.browser import BrowserClient
from webscraper.core.config import ScraperConfig
from webscraper.exceptions import BrowserClientError
from webscraper.scrapers.base import BaseScraper
from webscraper.validation.csv import CSVValidator, create_jao_validator


class JAOSeleniumScraper(BaseScraper):
    """Scraper for JAO maxNetPos data using Selenium browser automation.

    This scraper automates the browser to navigate the JAO website
    and trigger CSV downloads. Slower than API but works as fallback.

    Example:
        >>> config = ScraperConfig(output_dir=Path("./data"), headless=True)
        >>> with JAOSeleniumScraper(config) as scraper:
        ...     scraper.run(date(2024, 1, 1), date(2024, 1, 31))
    """

    def __init__(
        self,
        config: ScraperConfig,
        page_url: str = JAO_PAGE_URL,
        selectors: Optional[dict[str, str]] = None,
    ) -> None:
        """Initialize JAO Selenium scraper.

        Args:
            config: Scraper configuration
            page_url: JAO page URL
            selectors: CSS selectors for page elements
        """
        super().__init__(config)
        self.page_url = page_url
        self.selectors = selectors or JAO_SELECTORS
        self._browser: Optional[BrowserClient] = None

    @property
    def browser(self) -> BrowserClient:
        """Get browser client (lazy initialization)."""
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
        """Get validator for JAO CSV files."""
        return create_jao_validator()

    def download_for_date(self, target_date: date) -> Optional[Path]:
        """Download data for a specific date using Selenium.

        Args:
            target_date: Date to download data for

        Returns:
            Path to downloaded file, or None if failed
        """
        # Navigate to page
        self.browser.navigate(self.page_url)

        # Wait for page to load
        self.browser.wait_for_element("#container", timeout=30)
        time.sleep(3)  # Additional wait for JavaScript

        # Capture existing files before download
        existing_files = self.browser.get_existing_files()

        # Click download button to open popup
        self.browser.click(self.selectors["download_button"])
        time.sleep(2)

        # Format dates
        from_datetime_str = target_date.strftime("%Y-%m-%d 00:00")
        to_datetime_str = (target_date + timedelta(days=1)).strftime("%Y-%m-%d 00:00")

        # Set FROM datetime using JavaScript
        set_from_script = f"""
        var inputs = document.querySelectorAll('input.inputBorder');
        if (inputs.length >= 2) {{
            inputs[0].value = '{from_datetime_str}';
            var event = new Event('input', {{ bubbles: true }});
            inputs[0].dispatchEvent(event);
            event = new Event('change', {{ bubbles: true }});
            inputs[0].dispatchEvent(event);
        }}
        """
        self.browser.execute_script(set_from_script)
        time.sleep(0.5)

        # Set TO datetime using JavaScript
        set_to_script = f"""
        var inputs = document.querySelectorAll('input.inputBorder');
        if (inputs.length >= 2) {{
            inputs[1].value = '{to_datetime_str}';
            var event = new Event('input', {{ bubbles: true }});
            inputs[1].dispatchEvent(event);
            event = new Event('change', {{ bubbles: true }});
            inputs[1].dispatchEvent(event);
        }}
        """
        self.browser.execute_script(set_to_script)
        time.sleep(0.5)

        # Click CSV button
        click_csv_script = """
        var buttons = document.querySelectorAll('button.popupButton_GRkGEahdXf');
        for (var i = 0; i < buttons.length; i++) {
            if (buttons[i].textContent.trim() === 'CSV') {
                buttons[i].click();
                return true;
            }
        }
        return false;
        """
        clicked = self.browser.execute_script(click_csv_script)

        if not clicked:
            raise BrowserClientError("Could not find CSV button")

        # Wait for download
        downloaded_file = self.browser.wait_for_download(
            timeout=self.config.download_timeout,
            existing_files=existing_files,
        )

        if downloaded_file is None:
            raise BrowserClientError("Download timeout - no file received")

        # Process downloaded file
        output_path = self._process_download(downloaded_file, target_date)

        return output_path

    def _process_download(self, downloaded_file: Path, target_date: date) -> Path:
        """Process downloaded file (extract ZIP if needed).

        Args:
            downloaded_file: Path to downloaded file
            target_date: Target date for naming

        Returns:
            Path to final CSV file
        """
        output_filename = f"maxNetPos_{target_date.strftime('%Y%m%d')}.csv"
        output_path = self.config.output_dir / output_filename

        if zipfile.is_zipfile(downloaded_file):
            # Extract CSV from ZIP
            with zipfile.ZipFile(downloaded_file, "r") as zip_ref:
                csv_files = [f for f in zip_ref.namelist() if f.endswith(".csv")]

                if not csv_files:
                    raise BrowserClientError("No CSV file found in ZIP archive")

                csv_filename = csv_files[0]
                zip_ref.extract(csv_filename, self.config.output_dir)

                extracted_path = self.config.output_dir / csv_filename
                if output_path.exists():
                    output_path.unlink()
                extracted_path.rename(output_path)

            # Delete ZIP file
            downloaded_file.unlink()
        else:
            # Not a ZIP, just rename if needed
            if downloaded_file != output_path:
                if output_path.exists():
                    output_path.unlink()
                downloaded_file.rename(output_path)

        return output_path

    def cleanup(self) -> None:
        """Close browser."""
        if self._browser:
            self._browser.quit()
            self._browser = None


def run_jao_selenium_scraper(
    start_date: date = DEFAULT_START_DATE,
    end_date: date = DEFAULT_END_DATE,
    output_dir: Path = Path("./data"),
    headless: bool = True,
    browser: str = "chrome",
    verbose: bool = False,
) -> None:
    """Run the JAO Selenium scraper.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        output_dir: Directory to save downloaded files
        headless: Run browser in headless mode
        browser: Browser to use (chrome, firefox)
        verbose: Enable verbose logging
    """
    print("=" * 60)
    print("JAO MaxNetPos Selenium Scraper")
    print("=" * 60)
    print(f"Date range: {start_date} to {end_date}")
    print(f"Output directory: {output_dir}")
    print(f"Browser: {browser} ({'headless' if headless else 'headed'})")
    print("")

    config = ScraperConfig(
        output_dir=output_dir,
        headless=headless,
        browser=browser,
        verbose=verbose,
        requests_per_minute=20,  # Slower for Selenium
    )

    with JAOSeleniumScraper(config) as scraper:
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
        headless: bool = typer.Option(
            True,
            "--headless/--headed",
            help="Run browser in headless mode",
        ),
        browser: str = typer.Option(
            "chrome",
            "--browser",
            help="Browser to use",
        ),
        verbose: bool = typer.Option(
            False,
            "--verbose",
            "-v",
            help="Verbose output",
        ),
    ) -> None:
        """Download JAO maxNetPos data using Selenium."""
        from datetime import datetime

        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        run_jao_selenium_scraper(
            start_date=start,
            end_date=end,
            output_dir=output_dir,
            headless=headless,
            browser=browser,
            verbose=verbose,
        )

    typer.run(main)
