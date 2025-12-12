# Webscraper

For date-based web scraping with resume capability, rate limiting, and data validation.
Primary application: scrapiong Joint Allocation Office Publication site. Part of MLStrom project support for Hertie's Data Science Lab.

> see [quickstart](QUICKSTART.md)

## Features

- **Hybrid Approach**: Support for both API-based and Selenium browser automation
- **Resume Capability**: Tracks progress, automatically skips completed downloads
- **Adaptive Rate Limiting**: Respects API limits with automatic backoff
- **Data Validation**: Validates downloaded files (CSV, multiple encodings)
- **Type Safe**: Full type hints with strict mypy compatibility
- **Modern Python**: Pydantic configuration, Typer CLI, Python 3.9+

## Project Structure

```
webscraper/
├── src/webscraper/           # Core framework (installable package)
│   ├── core/                 # Infrastructure
│   │   ├── clients/          # HTTP and browser clients
│   │   ├── config.py         # Pydantic configuration
│   │   ├── rate_limiter.py   # Adaptive rate limiting
│   │   └── state.py          # Resume state management
│   ├── scrapers/             # Base scraper class
│   ├── validation/           # Data validators
│   └── utils/                # Progress tracking, dates
│
├── scripts/                  # Site-specific scrapers
│   ├── jao/                  # JAO Publication Tool scrapers
│   │   ├── api_scraper.py    # API-based (recommended)
│   │   └── scraper.py        # Selenium-based (fallback)
│   └── examples/             # Example implementations
│
├── tests/                    # Test suite
├── pyproject.toml            # Python packaging
└── Makefile                  # Dev commands
```

## Installation

### Quick Start

```bash
# Clone the repository
git clone https://github.com/henrybaker/webscraper.git
cd webscraper

# Install in development mode
pip install -e ".[dev]"
```

### Requirements

- Python 3.9+
- Chrome or Firefox (for Selenium-based scrapers)

## Usage

### JAO Publication Tool (maxNetPos)

The repository includes ready-to-use scrapers for the JAO Publication Tool:

**API-based (recommended - faster):**
```bash
python -m scripts.jao.api_scraper \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --output-dir ./data
```

**Selenium-based (fallback):**
```bash
python -m scripts.jao.scraper \
    --start-date 2024-01-01 \
    --end-date 2024-01-31 \
    --output-dir ./data \
    --headless
```

**Using Make:**
```bash
# Run API scraper with default dates
make jao-api

# Run Selenium scraper
make jao-selenium

# Check status
make status
```

### Creating Custom Scrapers

Create a new scraper by inheriting from `BaseScraper`:

```python
from datetime import date
from pathlib import Path
from typing import Optional

from webscraper import BaseScraper, CSVValidator, ScraperConfig


class MyScraper(BaseScraper):
    """Custom scraper for my data source."""

    def get_validator(self) -> CSVValidator:
        return CSVValidator(min_file_size=100, min_rows=1)

    def download_for_date(self, target_date: date) -> Optional[Path]:
        # Implement your download logic here
        # Return path to downloaded file or None
        pass


# Usage
config = ScraperConfig(output_dir=Path("./data"))
with MyScraper(config) as scraper:
    scraper.run(date(2024, 1, 1), date(2024, 12, 31))
```

See `scripts/examples/` for complete examples:
- `basic_api_scraper.py` - API-based scraper template
- `basic_selenium_scraper.py` - Browser automation template

### CLI Commands

```bash
# Check scraping session status
webscraper status --state-file ./data/scraper_state.json

# List dates (all or failed only)
webscraper list-dates --state-file ./data/scraper_state.json --failed-only

# Reset state (clear progress)
webscraper reset --state-file ./data/scraper_state.json

# Show version
webscraper version
```

## Configuration

`ScraperConfig` supports the following options:

| Option | Default | Description |
|--------|---------|-------------|
| `output_dir` | (required) | Directory for downloaded files |
| `state_file` | auto | State file path (defaults to output_dir/scraper_state.json) |
| `requests_per_minute` | 60 | Rate limit |
| `max_retries` | 3 | Max retry attempts per item |
| `retry_delay` | 60 | Seconds between retries |
| `request_timeout` | 30 | HTTP timeout in seconds |
| `download_timeout` | 300 | File download timeout |
| `validate_downloads` | True | Validate downloaded files |
| `verbose` | False | Enable verbose logging |
| `headless` | True | Run browser headless |
| `browser` | "chrome" | Browser choice (chrome/firefox) |

## Development

```bash
# Install dev dependencies
make install-dev

# Run tests
make test

# Run linter
make lint

# Run type checker
make typecheck

# Run all checks
make check

# Format code
make format
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Architecture

### Core Components

| Component | Description |
|-----------|-------------|
| `ScraperConfig` | Pydantic-validated configuration |
| `StateManager` | JSON-based progress tracking |
| `RateLimiter` | Token bucket with adaptive backoff |
| `HttpClient` | Requests-based client with retries |
| `BrowserClient` | Selenium wrapper with download handling |
| `CSVValidator` | Multi-encoding CSV validation |
| `BaseScraper` | Abstract base class for scrapers |

### Data Flow

```
ScraperConfig
     ↓
BaseScraper.run(start_date, end_date)
     ↓
┌────────────────────────────────┐
│ For each date:                 │
│  1. Check StateManager         │
│  2. Apply RateLimiter          │
│  3. download_for_date()        │
│  4. Validate with CSVValidator │
│  5. Update StateManager        │
└────────────────────────────────┘
     ↓
Progress summary
```
