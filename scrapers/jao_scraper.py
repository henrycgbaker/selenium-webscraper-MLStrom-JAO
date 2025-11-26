"""JAO Publication Tool scraper for maxNetPos data."""
from datetime import date
from pathlib import Path
from typing import Optional
import time

from selenium.webdriver.common.by import By

from .base import BaseScraper
from ..config import ScraperConfig
from ..utils.validation import CSVValidator, create_jao_validator
from ..core.api_client import APIClient, APIClientError
from ..core.selenium_client import SeleniumClient, SeleniumClientError


class JAOScraper(BaseScraper):
    """Scraper for JAO Publication Tool maxNetPos data.

    This scraper uses a hybrid approach:
    1. First attempts to download via direct API calls (if endpoint is discovered)
    2. Falls back to Selenium browser automation if API fails

    IMPORTANT: Before using this scraper, you must:
    1. Open https://publicationtool.jao.eu/core/maxNetPos in Chrome
    2. Open DevTools (F12) → Network tab
    3. Select a date and click download
    4. Find the API request and update API_ENDPOINT and request format below
    5. OR: Inspect the page elements and update the Selenium selectors
    """

    # JAO Configuration
    BASE_URL = "https://publicationtool.jao.eu/core"
    PAGE_URL = "https://publicationtool.jao.eu/core/maxNetPos"

    # API Configuration (to be discovered via DevTools)
    # TODO: Update these after inspecting network traffic
    API_ENDPOINT = "/api"  # PLACEHOLDER - inspect DevTools Network tab
    USE_API = False  # Set to True once API endpoint is configured

    # Selenium Selectors (to be discovered via page inspection)
    # TODO: Update these after inspecting page elements
    SELECTORS = {
        "start_date_input": "input[type='date']",  # PLACEHOLDER
        "end_date_input": "input[type='date']",  # PLACEHOLDER
        "download_button": "button.download",  # PLACEHOLDER
        "csv_button": "button.csv",  # PLACEHOLDER
    }

    def __init__(self, config: ScraperConfig):
        """Initialize JAO scraper.

        Args:
            config: Scraper configuration
        """
        super().__init__(config)

        # Initialize API client
        self.api_client = APIClient(
            base_url=self.BASE_URL,
            timeout=config.request_timeout,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
        )

        # Initialize Selenium client (lazy initialization)
        self.selenium_client: Optional[SeleniumClient] = None

    def get_validator(self) -> CSVValidator:
        """Get validator for JAO CSV files.

        Returns:
            CSVValidator configured for JAO data
        """
        return create_jao_validator()

    def download_for_date(self, target_date: date) -> Optional[Path]:
        """Download data for a specific date.

        Args:
            target_date: Date to download data for

        Returns:
            Path to downloaded file, or None if failed
        """
        # Try API first if configured
        if self.USE_API:
            try:
                return self._download_via_api(target_date)
            except APIClientError as e:
                if self.progress:
                    self.progress.log_debug(
                        f"API download failed for {target_date}: {e}, falling back to Selenium"
                    )

        # Fallback to Selenium
        try:
            return self._download_via_selenium(target_date)
        except SeleniumClientError as e:
            if self.progress:
                self.progress.log_debug(f"Selenium download failed for {target_date}: {e}")
            return None

    def _download_via_api(self, target_date: date) -> Path:
        """Download data via API.

        Args:
            target_date: Date to download

        Returns:
            Path to downloaded file

        Raises:
            APIClientError: If download fails

        NOTE: This method needs to be updated based on actual API structure
        discovered via browser DevTools Network tab.
        """
        # Format date for API (adjust format based on API requirements)
        date_str = target_date.strftime("%Y-%m-%d")

        # TODO: Update request format based on actual API
        # Example request format (adjust based on DevTools inspection):
        params = {
            "startDateTime": f"{date_str}T00:00:00",
            "endDateTime": f"{date_str}T23:59:59",
            # Add other required parameters
        }

        # Example for POST request with JSON body:
        # response = self.api_client.post(
        #     self.API_ENDPOINT,
        #     json=params
        # )

        # Generate output filename
        output_filename = f"maxNetPos_{target_date.strftime('%Y%m%d')}.csv"
        output_path = self.config.output_dir / output_filename

        # Download file
        # TODO: Adjust endpoint and parameters based on actual API
        downloaded_path = self.api_client.download_file(
            self.API_ENDPOINT, output_path, params=params
        )

        return downloaded_path

    def _download_via_selenium(self, target_date: date) -> Path:
        """Download data via Selenium browser automation.

        Args:
            target_date: Date to download

        Returns:
            Path to downloaded file

        Raises:
            SeleniumClientError: If download fails

        NOTE: Element selectors need to be updated based on actual page structure.
        Use browser DevTools to inspect and find correct selectors.
        """
        # Initialize Selenium client if needed
        if self.selenium_client is None:
            self.selenium_client = SeleniumClient(
                headless=self.config.headless,
                browser=self.config.browser,
                download_dir=self.config.output_dir,
                page_load_timeout=self.config.selenium_page_load_timeout,
                element_wait_timeout=self.config.selenium_element_wait_timeout,
            )
            self.selenium_client.start()

        # Navigate to page
        self.selenium_client.navigate(self.PAGE_URL)

        # Wait for page to load (wait for main container)
        self.selenium_client.wait_for_element("#container", timeout=30)

        # Additional wait for JavaScript to render
        time.sleep(3)

        # Format date string
        date_str = target_date.strftime("%Y-%m-%d")

        # TODO: Update selectors and interaction logic based on actual page structure
        # The following is a TEMPLATE that needs customization:

        try:
            # Example: Set start date
            # Option 1: If it's a standard date input
            # self.selenium_client.send_keys(self.SELECTORS["start_date_input"], date_str)

            # Option 2: If it's a custom date picker, you may need to:
            # - Click to open the picker
            # - Navigate to the correct month/year
            # - Click the specific day
            # Example:
            # self.selenium_client.click("#datePickerButton")
            # self.selenium_client.click(f"[data-date='{date_str}']")

            # Set end date (same as start for single-day download)
            # self.selenium_client.send_keys(self.SELECTORS["end_date_input"], date_str)

            # Click download/export button
            # self.selenium_client.click(self.SELECTORS["download_button"])

            # Click CSV format button (if separate)
            # self.selenium_client.click(self.SELECTORS["csv_button"])

            # Wait for download to complete
            downloaded_file = self.selenium_client.wait_for_download(
                timeout=self.config.download_timeout
            )

            if downloaded_file is None:
                raise SeleniumClientError("Download timeout - no file received")

            # Rename file to standard format if needed
            output_filename = f"maxNetPos_{target_date.strftime('%Y%m%d')}.csv"
            output_path = self.config.output_dir / output_filename

            if downloaded_file != output_path:
                downloaded_file.rename(output_path)

            return output_path

        except Exception as e:
            # Take screenshot for debugging
            if self.config.verbose and self.selenium_client:
                screenshot_path = (
                    self.config.output_dir / f"error_{target_date.strftime('%Y%m%d')}.png"
                )
                try:
                    self.selenium_client.screenshot(screenshot_path)
                    if self.progress:
                        self.progress.log_debug(f"Screenshot saved to {screenshot_path}")
                except Exception:
                    pass

            raise SeleniumClientError(f"Failed to download via Selenium: {e}")

    def cleanup(self):
        """Cleanup resources."""
        if self.api_client:
            self.api_client.close()
        if self.selenium_client:
            self.selenium_client.quit()


# Example of how to extend for other JAO datasets or websites:
class CustomWebsiteScraper(BaseScraper):
    """Template for creating scrapers for other websites.

    To create a scraper for a different website:
    1. Inherit from BaseScraper
    2. Implement download_for_date() method
    3. Implement get_validator() method
    4. Add any website-specific configuration
    """

    def __init__(self, config: ScraperConfig):
        super().__init__(config)
        # Add custom initialization

    def download_for_date(self, target_date: date) -> Optional[Path]:
        """Download data for a specific date."""
        # Implement download logic
        pass

    def get_validator(self) -> CSVValidator:
        """Get validator for downloaded files."""
        # Return configured validator
        return CSVValidator(min_file_size=100)
