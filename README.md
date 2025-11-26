# Web Scraper Architecture

*NB: v1 - this is a quick tool I created for Hertie's Data Science Lab ML Strom project (see [`QUICKSTART.md`](/Users/henrybaker/Repositories/jao_scraper/QUICKSTART.md)). I briefly worked on extending it out to a generic scraping tool, but this is not fully developed currently (26.11.2025, v1)*

A general-purpose Python framework for automating date-based web scraping tasks with built-in support for the JAO Publication Tool (i.e. the immediate use case).

## Features

- **Hybrid Approach**: API-based downloads + Selenium browser automation
- **Resume Capability**: Tracks progress, skips already downloaded dates
- **Rate Limiting**: Respects API rate limits with adaptive throttling
- **Progress Tracking**: Real-time progress bar and detailed logging
- **Data Validation**: Validates downloaded CSV files
- **Extensible**: Easy to add support for new websites

## Installation

### Prerequisites

- Python 3.8 or higher
- Chrome or Firefox browser installed

### Step 1: Install Dependencies

```bash
cd jao_scraper
pip install -r requirements.txt
```

## Quick Start - JAO Publication Tool

### IMPORTANT: Configuration Required

Before running the scraper, you **must** configure it for the website (here: JAO publications site):

#### Step 1: Discover API Endpoint or Page Elements

1. Open Chrome and navigate to site (here: https://publicationtool.jao.eu/core/maxNetPos)

2. Open Chrome DevTools:
   - Press F12, or
   - Right-click → Inspect

**Option A: Find API Endpoint (Recommended)**

1. Go to Network tab in DevTools
2. Select a date range and click download
3. Look for XHR/Fetch requests to `/core/api` or similar
4. Click on the request to see:
   - Request URL
   - Request Method (GET/POST)
   - Request Payload (JSON format)
   - Response format
5. Update `scrapers/jao_scraper.py`:
   - Set `USE_API = True`
   - Update `API_ENDPOINT` with the correct path
   - Update `_download_via_api()` method with correct request format

**Option B: Find Page Elements (Fallback)**

1. Right-click on the date picker → Inspect
2. Note the element's ID, class, or other selectors
3. Repeat for the download button
4. Update `SELECTORS` dictionary in `scrapers/jao_scraper.py`
5. Update `_download_via_selenium()` method with correct interaction logic

#### Step 2: Run the Scraper

Download data from June 8, 2022 to December 31, 2024:

```bash
python main.py jao \
  --start-date 2022-06-08 \
  --end-date 2024-12-31 \
  --output-dir ./jao_data \
  --rate-limit 60 \
  --verbose
```

### Basic Usage

```bash
# Download JAO data for a date range
python main.py jao -s 2022-06-08 -e 2024-12-31 -o ./data

# Resume a previous run
python main.py jao -s 2022-06-08 -e 2024-12-31 -o ./data --resume

# Check status
python main.py status -s ./data/scraper_state.json

# List failed dates
python main.py list-dates -s ./data/scraper_state.json --failed-only

# Reset state
python main.py reset -s ./data/scraper_state.json
```

### Command Reference

#### `jao` - Download JAO data

```bash
python main.py jao [OPTIONS]

Options:
  -s, --start-date DATE        Start date (YYYY-MM-DD) [required]
  -e, --end-date DATE          End date (YYYY-MM-DD) [required]
  -o, --output-dir PATH        Output directory [default: ./data]
  --resume / --no-resume       Resume from previous run [default: resume]
  --validate / --no-validate   Validate files [default: validate]
  -v, --verbose / -q, --quiet  Verbose output [default: quiet]
  --headless / --headed        Browser mode [default: headless]
  --browser [chrome|firefox]   Browser choice [default: chrome]
  --rate-limit INTEGER         Requests per minute [default: 60]
  --log-file PATH             Log file path (optional)
```

#### `status` - Show scraping status

```bash
python main.py status -s ./data/scraper_state.json
```

#### `list-dates` - List all dates

```bash
python main.py list-dates -s ./data/scraper_state.json [--failed-only]
```

#### `reset` - Reset state

```bash
python main.py reset -s ./data/scraper_state.json
```

## Architecture

### Project Structure

```
jao_scraper/
├── scrapers/
│   ├── base.py           # Abstract base scraper class
│   ├── jao_scraper.py    # JAO-specific implementation
│   └── __init__.py
├── core/
│   ├── api_client.py     # HTTP API client with retry logic
│   ├── selenium_client.py # Selenium browser automation
│   ├── rate_limiter.py   # Rate limiting handler
│   └── __init__.py
├── utils/
│   ├── progress.py       # Progress tracking and logging
│   ├── validation.py     # CSV validation utilities
│   ├── state.py          # Resume state management
│   └── __init__.py
├── config.py             # Configuration management
├── main.py               # CLI entry point
├── requirements.txt
└── README.md
```

### Key Components

#### BaseScraper (scrapers/base.py)

Abstract class providing:
- Date range generation
- State management for resume capability
- Progress tracking
- Rate limiting
- Data validation hooks

To create a new scraper, extend this class and implement:
- `download_for_date(date) -> Path`: Download logic for a single date
- `get_validator() -> CSVValidator`: Return configured validator

#### StateManager (utils/state.py)

Tracks download status for each date:
- `PENDING`: Not yet attempted
- `IN_PROGRESS`: Currently downloading
- `COMPLETED`: Successfully downloaded and validated
- `FAILED`: Download or validation failed

State is persisted to JSON file for resume capability.

#### RateLimiter (core/rate_limiter.py)

Token bucket rate limiter that:
- Enforces maximum requests per minute
- Adapts to 429 (Too Many Requests) responses
- Automatically backs off when rate limited

#### APIClient (core/api_client.py)

HTTP client with:
- Automatic retries on failure
- 429 handling with Retry-After header support
- File download support
- Session management

#### SeleniumClient (core/selenium_client.py)

Browser automation with:
- Chrome and Firefox support
- Headless mode
- Download directory configuration
- Element waiting with timeouts
- Screenshot capability for debugging

## Extending for Other Websites

### Creating a New Scraper

1. Create a new file in `scrapers/` (e.g., `custom_scraper.py`)
2. Extend `BaseScraper`:

```python
from datetime import date
from pathlib import Path
from typing import Optional

from .base import BaseScraper
from ..config import ScraperConfig
from ..utils.validation import CSVValidator


class CustomScraper(BaseScraper):
    """Scraper for custom website."""

    def __init__(self, config: ScraperConfig):
        super().__init__(config)
        # Initialize API client, Selenium client, etc.

    def download_for_date(self, target_date: date) -> Optional[Path]:
        """Download data for a specific date."""
        # Implement download logic
        # Return Path to downloaded file or None
        pass

    def get_validator(self) -> CSVValidator:
        """Get validator for downloaded files."""
        return CSVValidator(
            min_file_size=100,
            required_columns=["date", "value"],
            min_rows=1,
        )
```

3. Add a CLI command in `main.py`:

```python
@cli.command()
@click.option("--start-date", "-s", ...)
@click.option("--end-date", "-e", ...)
def custom(start_date, end_date, ...):
    """Download custom website data."""
    config = ScraperConfig(...)
    with CustomScraper(config) as scraper:
        scraper.run(start_date, end_date)
```

### Example: API-Based Scraper

```python
def download_for_date(self, target_date: date) -> Optional[Path]:
    from core.api_client import APIClient

    client = APIClient("https://api.example.com")
    client.set_headers({"Authorization": "Bearer TOKEN"})

    params = {
        "date": target_date.strftime("%Y-%m-%d"),
        "format": "csv"
    }

    output_path = self.config.output_dir / f"data_{target_date:%Y%m%d}.csv"
    return client.download_file("/export", output_path, params=params)
```

### Example: Selenium-Based Scraper

```python
def download_for_date(self, target_date: date) -> Optional[Path]:
    from core.selenium_client import SeleniumClient
    from selenium.webdriver.common.by import By

    client = SeleniumClient(
        headless=self.config.headless,
        download_dir=self.config.output_dir
    )
    client.start()

    # Navigate and interact
    client.navigate("https://example.com/data")
    client.send_keys("#date-input", target_date.strftime("%Y-%m-%d"))
    client.click("#download-button")

    # Wait for download
    downloaded_file = client.wait_for_download(timeout=60)
    client.quit()

    return downloaded_file
```

## Troubleshooting

### Common Issues

**1. JAO scraper not downloading files**

- Ensure you've configured the API endpoint or Selenium selectors
- Check `scrapers/jao_scraper.py` for TODO comments
- Run with `--verbose` to see detailed logs
- Check screenshots in output directory if Selenium fails

**2. Rate limiting (429 errors)**

- Reduce `--rate-limit` value (default: 60 req/min)
- JAO limit is 100 req/min, but conservative is safer
- The scraper will automatically back off and retry

**3. Selenium browser not starting**

- Install Chrome or Firefox browser
- Chrome driver is auto-installed via `webdriver-manager`
- Try `--browser firefox` if Chrome fails

**4. Downloads incomplete or corrupted**

- Enable validation: `--validate` (default)
- Check log file for validation errors
- Increase timeout values in `config.py`

**5. Missing date picker elements**

- Dates may not have data (normal)
- Check `--failed-only` dates to investigate
- Some dates return empty files (validator catches this)

### Debug Mode

Run with verbose logging and headed browser:

```bash
python main.py jao \
  -s 2024-01-01 -e 2024-01-03 \
  -o ./test \
  --verbose \
  --headed \
  --log-file ./debug.log
```

This will:
- Show detailed logs
- Display browser window
- Save logs to file
- Take screenshots on errors

## Performance

### Expected Performance

- **API mode**: ~60 downloads/minute (rate limit dependent)
- **Selenium mode**: ~10-20 downloads/minute (slower due to browser overhead)

### Optimization Tips

1. **Use API when possible**: Much faster than Selenium
2. **Adjust rate limit**: Balance speed vs. server load
3. **Headless mode**: Faster than headed browser
4. **Disable validation**: Skip with `--no-validate` (not recommended)

### Estimating Runtime

For JAO data (June 8, 2022 → Dec 31, 2024):
- Total days: ~930 days
- API mode: ~15-20 minutes
- Selenium mode: ~45-90 minutes

## State File Format

The state file (`scraper_state.json`) tracks all downloads:

```json
{
  "created_at": "2024-01-01T10:00:00",
  "last_updated": "2024-01-01T10:30:00",
  "downloads": {
    "2024-01-01": {
      "status": "completed",
      "file_path": "/path/to/file.csv",
      "attempts": 1,
      "created_at": "2024-01-01T10:15:00"
    },
    "2024-01-02": {
      "status": "failed",
      "error": "Validation failed",
      "attempts": 3
    }
  },
  "metadata": {}
}
```

## License

MIT License - feel free to use and modify for your needs.

## Contributing

To add support for a new website:
1. Create a scraper in `scrapers/`
2. Add CLI command in `main.py`
3. Update this README with usage examples
4. Test thoroughly with small date ranges first

## Credits

Built using:
- [Selenium](https://www.selenium.dev/) - Browser automation
- [Requests](https://requests.readthedocs.io/) - HTTP client
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Pandas](https://pandas.pydata.org/) - CSV validation
- [tqdm](https://tqdm.github.io/) - Progress bars
