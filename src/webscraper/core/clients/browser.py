"""Selenium-based browser automation client."""

import time
from pathlib import Path
from types import TracebackType
from typing import Any, Optional

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from webscraper.exceptions import BrowserClientError


class BrowserClient:
    """Browser automation client using Selenium.

    Features:
    - Chrome and Firefox support
    - Headless mode
    - Automatic webdriver management
    - Download directory configuration
    - Element waiting with timeouts
    - Screenshot capability for debugging

    Example:
        >>> with BrowserClient(headless=True, download_dir=Path("./downloads")) as client:
        ...     client.navigate("https://example.com")
        ...     client.click("#download-button")
        ...     file_path = client.wait_for_download(timeout=60)
    """

    def __init__(
        self,
        headless: bool = True,
        browser: str = "chrome",
        download_dir: Optional[Path] = None,
        page_load_timeout: int = 30,
        element_wait_timeout: int = 20,
    ) -> None:
        """Initialize Selenium client.

        Args:
            headless: Run browser in headless mode
            browser: Browser to use (chrome, firefox)
            download_dir: Directory for downloads
            page_load_timeout: Page load timeout in seconds
            element_wait_timeout: Element wait timeout in seconds
        """
        self.headless = headless
        self.browser = browser.lower()
        self.download_dir = download_dir
        self.page_load_timeout = page_load_timeout
        self.element_wait_timeout = element_wait_timeout
        self._driver: Optional[WebDriver] = None
        self._wait: Optional[WebDriverWait[WebDriver]] = None

    def start(self) -> None:
        """Start the browser."""
        if self._driver is not None:
            return

        if self.browser == "chrome":
            self._driver = self._create_chrome_driver()
        elif self.browser == "firefox":
            self._driver = self._create_firefox_driver()
        else:
            raise BrowserClientError(f"Unsupported browser: {self.browser}")

        self._driver.set_page_load_timeout(self.page_load_timeout)
        self._wait = WebDriverWait(self._driver, self.element_wait_timeout)

    def _create_chrome_driver(self) -> webdriver.Chrome:
        """Create Chrome webdriver."""
        options = webdriver.ChromeOptions()

        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # Set download directory
        if self.download_dir:
            self.download_dir.mkdir(parents=True, exist_ok=True)
            prefs = {
                "download.default_directory": str(self.download_dir.absolute()),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
            }
            options.add_experimental_option("prefs", prefs)

        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def _create_firefox_driver(self) -> webdriver.Firefox:
        """Create Firefox webdriver."""
        options = webdriver.FirefoxOptions()

        if self.headless:
            options.add_argument("--headless")

        # Set download directory
        if self.download_dir:
            self.download_dir.mkdir(parents=True, exist_ok=True)
            options.set_preference("browser.download.folderList", 2)
            options.set_preference(
                "browser.download.dir", str(self.download_dir.absolute())
            )
            options.set_preference("browser.download.useDownloadDir", True)
            options.set_preference(
                "browser.helperApps.neverAsk.saveToDisk", "text/csv,application/csv"
            )

        service = FirefoxService(GeckoDriverManager().install())
        return webdriver.Firefox(service=service, options=options)

    def navigate(self, url: str) -> None:
        """Navigate to URL.

        Args:
            url: URL to navigate to
        """
        if not self._driver:
            raise BrowserClientError("Driver not started. Call start() first.")

        try:
            self._driver.get(url)
        except TimeoutException as e:
            raise BrowserClientError(f"Page load timeout for {url}", cause=e)

    def wait_for_element(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None,
    ) -> WebElement:
        """Wait for element to be present.

        Args:
            selector: Element selector
            by: Selector type (default: CSS_SELECTOR)
            timeout: Custom timeout (uses default if not provided)

        Returns:
            WebElement

        Raises:
            BrowserClientError: If element not found
        """
        if not self._driver:
            raise BrowserClientError("Driver not started. Call start() first.")

        wait_time = timeout if timeout is not None else self.element_wait_timeout
        wait: WebDriverWait[WebDriver] = WebDriverWait(self._driver, wait_time)

        try:
            element = wait.until(EC.presence_of_element_located((by, selector)))
            return element  # type: ignore[return-value]
        except TimeoutException as e:
            raise BrowserClientError(
                f"Element not found: {selector} (waited {wait_time}s)", cause=e
            )

    def wait_for_clickable(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None,
    ) -> WebElement:
        """Wait for element to be clickable.

        Args:
            selector: Element selector
            by: Selector type
            timeout: Custom timeout

        Returns:
            WebElement
        """
        if not self._driver:
            raise BrowserClientError("Driver not started. Call start() first.")

        wait_time = timeout if timeout is not None else self.element_wait_timeout
        wait: WebDriverWait[WebDriver] = WebDriverWait(self._driver, wait_time)

        try:
            element = wait.until(EC.element_to_be_clickable((by, selector)))
            return element  # type: ignore[return-value]
        except TimeoutException as e:
            raise BrowserClientError(
                f"Element not clickable: {selector} (waited {wait_time}s)", cause=e
            )

    def click(self, selector: str, by: By = By.CSS_SELECTOR) -> None:
        """Click an element.

        Args:
            selector: Element selector
            by: Selector type
        """
        element = self.wait_for_clickable(selector, by)
        element.click()

    def send_keys(self, selector: str, text: str, by: By = By.CSS_SELECTOR) -> None:
        """Send keys to an element.

        Args:
            selector: Element selector
            text: Text to send
            by: Selector type
        """
        element = self.wait_for_element(selector, by)
        element.clear()
        element.send_keys(text)

    def get_element(
        self, selector: str, by: By = By.CSS_SELECTOR
    ) -> Optional[WebElement]:
        """Get element by selector.

        Args:
            selector: Element selector
            by: Selector type

        Returns:
            WebElement or None if not found
        """
        if not self._driver:
            raise BrowserClientError("Driver not started. Call start() first.")

        try:
            return self._driver.find_element(by, selector)
        except NoSuchElementException:
            return None

    def get_elements(self, selector: str, by: By = By.CSS_SELECTOR) -> list[WebElement]:
        """Get all matching elements.

        Args:
            selector: Element selector
            by: Selector type

        Returns:
            List of WebElements
        """
        if not self._driver:
            raise BrowserClientError("Driver not started. Call start() first.")

        return self._driver.find_elements(by, selector)

    def get_existing_files(self) -> set[Path]:
        """Get set of existing files in download directory.

        Call this before triggering a download to track what's new.

        Returns:
            Set of file paths currently in download directory
        """
        if not self.download_dir:
            return set()
        return {f for f in self.download_dir.iterdir() if f.is_file()}

    def wait_for_download(
        self,
        timeout: int = 60,
        existing_files: Optional[set[Path]] = None,
    ) -> Optional[Path]:
        """Wait for a file to be downloaded.

        Args:
            timeout: Maximum time to wait in seconds
            existing_files: Set of files that existed before download started.
                           If provided, only new files will be considered.

        Returns:
            Path to downloaded file or None
        """
        if not self.download_dir:
            raise BrowserClientError("Download directory not set")

        # If no existing_files provided, get current snapshot (less reliable)
        if existing_files is None:
            existing_files = self.get_existing_files()

        end_time = time.time() + timeout

        while time.time() < end_time:
            # Check for .crdownload (Chrome) or .part (Firefox) files
            temp_files = list(self.download_dir.glob("*.crdownload")) + list(
                self.download_dir.glob("*.part")
            )

            if temp_files:
                # Download in progress, wait
                time.sleep(1)
                continue

            # Look for new files (files that didn't exist before)
            current_files = {f for f in self.download_dir.iterdir() if f.is_file()}
            new_files = current_files - existing_files

            # Filter out hidden files and common non-download files
            new_files = {
                f
                for f in new_files
                if not f.name.startswith(".")
                and not f.name.endswith(".json")  # Exclude state files
            }

            if new_files:
                # Return the newest new file
                newest_file = max(new_files, key=lambda f: f.stat().st_mtime)
                return newest_file

            time.sleep(1)

        return None

    def execute_script(self, script: str) -> Any:
        """Execute JavaScript.

        Args:
            script: JavaScript code to execute

        Returns:
            Script result
        """
        if not self._driver:
            raise BrowserClientError("Driver not started. Call start() first.")

        return self._driver.execute_script(script)

    def screenshot(self, output_path: Path) -> None:
        """Take screenshot.

        Args:
            output_path: Path to save screenshot
        """
        if not self._driver:
            raise BrowserClientError("Driver not started. Call start() first.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._driver.save_screenshot(str(output_path))

    def quit(self) -> None:
        """Close the browser."""
        if self._driver:
            self._driver.quit()
            self._driver = None
            self._wait = None

    def close(self) -> None:
        """Alias for quit() for protocol compatibility."""
        self.quit()

    def __enter__(self) -> "BrowserClient":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit."""
        self.quit()

    @property
    def driver(self) -> Optional[WebDriver]:
        """Access the underlying WebDriver (for advanced usage)."""
        return self._driver
