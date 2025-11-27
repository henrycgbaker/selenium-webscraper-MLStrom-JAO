#!/usr/bin/env python3
"""
JAO MaxNetPos Data Scraper 

This standalone script downloads the complete JAO maxNetPos dataset from June 8, 2022 to December 31, 2024.

USAGE:
    1. Install dependencies:
       pip install selenium webdriver-manager pandas tqdm python-dateutil

    2. Run the script:
       python scrape_jao.py

    The script will:
    - Download data to ./data directory
    - Save progress to ./data/scraper_state.json (supports resume)

REQUIREMENTS:
    - Python 3.8+
    - Chrome browser installed
"""

import json
import time
import zipfile
import threading
import sys
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Set, Dict
from collections import deque
from enum import Enum

# Third-party imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from dateutil.rrule import rrule, DAILY
from tqdm import tqdm
import pandas as pd

# =============================================================================
# CONFIGURATION
# =============================================================================

START_DATE = date(2022, 6, 8)
END_DATE = date(2024, 12, 31)

OUTPUT_DIR = Path("./data")
STATE_FILE = OUTPUT_DIR / "scraper_state.json"

REQUESTS_PER_MINUTE = 60
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds

PAGE_LOAD_TIMEOUT = 30
ELEMENT_WAIT_TIMEOUT = 20
DOWNLOAD_TIMEOUT = 300

PAGE_URL = "https://publicationtool.jao.eu/core/maxNetPos"

# Selenium selectors
SELECTORS = {
    "download_button": "button.pageButton_rpP4hV2OM0",
    "csv_button": "button.popupButton_GRkGEahdXf",
}


# =============================================================================
# DOWNLOAD STATUS ENUM
# =============================================================================

class DownloadStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# STATE MANAGER (Resume Capability)
# =============================================================================

class StateManager:
    """Manages scraper state for resume capability."""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state: Dict = self._load_state()
        self._lock = threading.Lock()

    def _load_state(self) -> Dict:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._init_state()
        return self._init_state()

    def _init_state(self) -> Dict:
        return {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "downloads": {},
            "metadata": {},
        }

    def _save_state(self):
        with self._lock:
            self.state["last_updated"] = datetime.now().isoformat()
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self.state, indent=2, fp=f)

    def get_status(self, date_key: str) -> DownloadStatus:
        with self._lock:
            if date_key in self.state["downloads"]:
                return DownloadStatus(self.state["downloads"][date_key]["status"])
            return DownloadStatus.PENDING

    def set_status(self, date_key: str, status: DownloadStatus,
                   file_path: Optional[str] = None, error: Optional[str] = None):
        with self._lock:
            if date_key not in self.state["downloads"]:
                self.state["downloads"][date_key] = {
                    "status": status.value,
                    "file_path": file_path,
                    "error": error,
                    "attempts": 0,
                    "created_at": datetime.now().isoformat(),
                }
            else:
                self.state["downloads"][date_key]["status"] = status.value
                if file_path:
                    self.state["downloads"][date_key]["file_path"] = file_path
                if error:
                    self.state["downloads"][date_key]["error"] = error
                self.state["downloads"][date_key]["updated_at"] = datetime.now().isoformat()

            if status in [DownloadStatus.IN_PROGRESS, DownloadStatus.FAILED]:
                self.state["downloads"][date_key]["attempts"] += 1

        self._save_state()

    def get_completed_dates(self) -> Set[str]:
        with self._lock:
            return {
                date_key for date_key, info in self.state["downloads"].items()
                if info["status"] == DownloadStatus.COMPLETED.value
            }

    def get_pending_dates(self, all_dates: List[str]) -> List[str]:
        completed = self.get_completed_dates()
        return [d for d in all_dates if d not in completed]

    def get_attempts(self, date_key: str) -> int:
        with self._lock:
            if date_key in self.state["downloads"]:
                return self.state["downloads"][date_key].get("attempts", 0)
            return 0

    def get_summary(self) -> Dict:
        with self._lock:
            total = len(self.state["downloads"])
            completed = sum(1 for info in self.state["downloads"].values()
                            if info["status"] == DownloadStatus.COMPLETED.value)
            failed = sum(1 for info in self.state["downloads"].values()
                         if info["status"] == DownloadStatus.FAILED.value)
            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "success_rate": (completed / total * 100) if total > 0 else 0,
            }


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Token bucket rate limiter for requests."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_times = deque(maxlen=requests_per_minute)
        self._lock = threading.Lock()

    def wait_if_needed(self):
        with self._lock:
            now = time.time()
            if len(self.request_times) < self.requests_per_minute:
                self.request_times.append(now)
                return

            oldest_request = self.request_times[0]
            time_since_oldest = now - oldest_request

            if time_since_oldest < 60.0:
                wait_time = 60.0 - time_since_oldest
                time.sleep(wait_time)
                now = time.time()

            self.request_times.append(now)

    def on_429_response(self, retry_after: int = 60):
        with self._lock:
            time.sleep(retry_after)
            self.request_times.clear()


# =============================================================================
# CSV VALIDATOR
# =============================================================================

class CSVValidator:
    """Validates downloaded CSV files."""

    def __init__(self, min_file_size: int = 50):
        self.min_file_size = min_file_size

    def validate_file(self, file_path: Path) -> bool:
        if not file_path.exists():
            raise ValueError(f"File does not exist: {file_path}")

        file_size = file_path.stat().st_size
        if file_size < self.min_file_size:
            raise ValueError(f"File too small ({file_size} bytes)")

        # Try to read as CSV
        encodings = ['utf-8', 'iso-8859-1', 'windows-1252']
        delimiters = [',', ';']
        df = None

        for encoding in encodings:
            for delimiter in delimiters:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, sep=delimiter,
                                     encoding_errors='ignore')
                    if len(df.columns) > 1:
                        return True
                except Exception:
                    continue

        if df is None or len(df.columns) <= 1:
            raise ValueError("Failed to read CSV with any encoding/delimiter")

        return True


# =============================================================================
# SELENIUM CLIENT
# =============================================================================

class SeleniumClient:
    """Browser automation client using Selenium."""

    def __init__(self, download_dir: Path, headless: bool = True):
        self.download_dir = download_dir
        self.headless = headless
        self.driver = None
        self.wait = None

    def start(self):
        if self.driver is not None:
            return

        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        self.download_dir.mkdir(parents=True, exist_ok=True)
        prefs = {
            "download.default_directory": str(self.download_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
        }
        options.add_experimental_option("prefs", prefs)

        service = ChromeService(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        self.wait = WebDriverWait(self.driver, ELEMENT_WAIT_TIMEOUT)

    def navigate(self, url: str):
        if not self.driver:
            raise RuntimeError("Driver not started. Call start() first.")
        try:
            self.driver.get(url)
        except TimeoutException:
            raise RuntimeError(f"Page load timeout for {url}")

    def wait_for_element(self, selector: str, timeout: Optional[int] = None):
        if not self.driver:
            raise RuntimeError("Driver not started.")
        wait_time = timeout if timeout else ELEMENT_WAIT_TIMEOUT
        wait = WebDriverWait(self.driver, wait_time)
        try:
            return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        except TimeoutException:
            raise RuntimeError(f"Element not found: {selector}")

    def click(self, selector: str):
        element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        element.click()

    def get_existing_files(self) -> set:
        return {f for f in self.download_dir.iterdir() if f.is_file()}

    def wait_for_download(self, timeout: int = 60, existing_files: Optional[set] = None) -> Optional[Path]:
        if existing_files is None:
            existing_files = self.get_existing_files()

        end_time = time.time() + timeout

        while time.time() < end_time:
            # Check for in-progress downloads
            temp_files = list(self.download_dir.glob("*.crdownload")) + \
                         list(self.download_dir.glob("*.part"))
            if temp_files:
                time.sleep(1)
                continue

            # Look for new files
            current_files = {f for f in self.download_dir.iterdir() if f.is_file()}
            new_files = current_files - existing_files
            new_files = {f for f in new_files
                         if not f.name.startswith(".")
                         and not f.name.endswith(".json")}

            if new_files:
                return max(new_files, key=lambda f: f.stat().st_mtime)

            time.sleep(1)

        return None

    def execute_script(self, script: str):
        if not self.driver:
            raise RuntimeError("Driver not started.")
        return self.driver.execute_script(script)

    def screenshot(self, output_path: Path):
        if self.driver:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self.driver.save_screenshot(str(output_path))

    def quit(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None


# =============================================================================
# JAO SCRAPER
# =============================================================================

def download_for_date(client: SeleniumClient, target_date: date, output_dir: Path) -> Optional[Path]:
    """Download data for a specific date using Selenium."""

    # Navigate to page
    client.navigate(PAGE_URL)
    client.wait_for_element("#container", timeout=30)
    time.sleep(3)  # Wait for JavaScript

    try:
        # Capture existing files
        existing_files = client.get_existing_files()

        # Click the download button to open popup
        client.click(SELECTORS["download_button"])
        time.sleep(2)

        # Format dates
        from_datetime_str = target_date.strftime("%Y-%m-%d 00:00")
        to_datetime_str = (target_date + timedelta(days=1)).strftime("%Y-%m-%d 00:00")

        # Set FROM datetime via JavaScript
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
        client.execute_script(set_from_script)
        time.sleep(0.5)

        # Set TO datetime via JavaScript
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
        client.execute_script(set_to_script)
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
        clicked = client.execute_script(click_csv_script)
        if not clicked:
            raise RuntimeError("Could not find CSV button")

        # Wait for download
        downloaded_file = client.wait_for_download(timeout=DOWNLOAD_TIMEOUT, existing_files=existing_files)
        if downloaded_file is None:
            raise RuntimeError("Download timeout - no file received")

        # Define final output path
        output_filename = f"maxNetPos_{target_date.strftime('%Y%m%d')}.csv"
        output_path = output_dir / output_filename

        # Handle ZIP files
        if zipfile.is_zipfile(downloaded_file):
            with zipfile.ZipFile(downloaded_file, 'r') as zip_ref:
                csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
                if not csv_files:
                    raise RuntimeError("No CSV file found in ZIP")
                csv_filename = csv_files[0]
                zip_ref.extract(csv_filename, output_dir)
                extracted_path = output_dir / csv_filename
                if output_path.exists():
                    output_path.unlink()
                extracted_path.rename(output_path)
            downloaded_file.unlink()
        else:
            if downloaded_file != output_path:
                if output_path.exists():
                    output_path.unlink()
                downloaded_file.rename(output_path)

        return output_path

    except Exception as e:
        raise RuntimeError(f"Failed to download: {e}")


# =============================================================================
# MAIN SCRAPER LOOP
# =============================================================================

def run_scraper():
    """Run the full JAO scraper."""

    print("=" * 60)
    print("JAO MaxNetPos Full Data Scraper")
    print("=" * 60)
    print(f"Date range: {START_DATE} to {END_DATE}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize components
    state = StateManager(STATE_FILE)
    rate_limiter = RateLimiter(REQUESTS_PER_MINUTE)
    validator = CSVValidator()

    # Generate date range
    all_dates = list(rrule(DAILY, dtstart=START_DATE, until=END_DATE))
    date_strings = [d.strftime("%Y-%m-%d") for d in all_dates]

    # Get pending dates (for resume)
    pending_dates = state.get_pending_dates(date_strings)
    pending_date_objects = [datetime.strptime(d, "%Y-%m-%d").date() for d in pending_dates]

    print(f"Total dates: {len(all_dates)}")
    print(f"Already completed: {len(all_dates) - len(pending_date_objects)}")
    print(f"To download: {len(pending_date_objects)}")
    print("")

    if not pending_date_objects:
        print("All dates already downloaded!")
        return

    # Initialize Selenium
    client = SeleniumClient(download_dir=OUTPUT_DIR, headless=True)
    client.start()

    completed = 0
    failed = 0

    try:
        # Process each date with progress bar
        pbar = tqdm(pending_date_objects, desc="Downloading", unit="day",
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")

        for target_date in pbar:
            date_str = target_date.strftime("%Y-%m-%d")
            pbar.set_postfix_str(date_str)

            try:
                # Check max attempts
                attempts = state.get_attempts(date_str)
                if attempts >= MAX_RETRIES:
                    continue

                # Mark as in progress
                state.set_status(date_str, DownloadStatus.IN_PROGRESS)

                # Rate limiting
                rate_limiter.wait_if_needed()

                # Download
                file_path = download_for_date(client, target_date, OUTPUT_DIR)

                if file_path is None:
                    state.set_status(date_str, DownloadStatus.FAILED, error="Download returned None")
                    failed += 1
                    continue

                # Validate
                try:
                    validator.validate_file(file_path)
                except Exception as e:
                    state.set_status(date_str, DownloadStatus.FAILED,
                                     file_path=str(file_path), error=f"Validation failed: {e}")
                    failed += 1
                    continue

                # Success
                state.set_status(date_str, DownloadStatus.COMPLETED, file_path=str(file_path))
                completed += 1

            except Exception as e:
                error_msg = str(e)
                state.set_status(date_str, DownloadStatus.FAILED, error=error_msg)
                failed += 1

                if "429" in error_msg or "rate limit" in error_msg.lower():
                    rate_limiter.on_429_response(RETRY_DELAY)

        pbar.close()

    finally:
        client.quit()

    # Print summary
    print("\n" + "=" * 60)
    print("SCRAPING SUMMARY")
    print("=" * 60)
    summary = state.get_summary()
    print(f"Total tracked: {summary['total']}")
    print(f"Completed: {summary['completed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success rate: {summary['success_rate']:.1f}%")
    print("=" * 60)
    print("\nDone!")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    run_scraper()
